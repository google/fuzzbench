from pwn import *
import pandas as pd

context.log_level = 'WARN'
MACHINES = (
    'fuzzbench1', 'fuzzbench2', 'fuzzbench3', 'webster',
    'fuzzbench5', 'wood', 'fuzzbench7', 'fuzzbench8',
    'fuzzbench9', 'fuzzbench10', 'fuzzbench11'
)
COLUMNS = ['timestamp', 'machine']
DISK_COLUMNS = ['fs', 'blocks_1k', 'used', 'available', 'use_percent', 'mounted_on']
RAM_COLUMNS = ['total', 'used', 'free', 'shared', 'buffered', 'available']
def get_snapshot():
    individual_results = []
    with log.progress('Collecting disk usage snapshot', level=logging.WARN) as prog:
        for m in MACHINES:
            with process(['ssh', m]) as r:
                r.sendline(b"echo 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'; df /nvme; free; exit")
                try:
                    r.readuntil(b'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n', timeout=10)
                    lines = r.recvall(timeout=10).decode('utf-8').strip().split('\n')
                except TimeoutError:
                    log.warn('TimeoutError on', m)
                    continue
                except EOFError:
                    log.warn("EOF on", m)
                    continue
                if len(lines) != 5:
                    log.warn("Unexpected response %s => %r", m, lines)
                    continue
                prog.status("@%s => %s", m, lines[1])

                keys = lines[0] # can't be used, because it can't be split directly, just ensure it matches
                assert keys.strip().split() == 'Filesystem      1K-blocks       Used  Available Use% Mounted on'.split()

                fs, blocks_1k, used, available, use_percent, mounted_on = lines[1].strip().split(maxsplit=5)
                blocks_1k = int(blocks_1k)
                used = int(used)
                available = int(available)
                assert use_percent[-1] == '%'
                use_percent = int(use_percent[:-1])

                keys_ram = lines[2]
                assert keys_ram.strip().split() == '              total        used        free      shared  buff/cache   available'.split()
                assert lines[3].startswith('Mem:')
                assert lines[4].startswith('Swap:')
                ram_total, ram_used, ram_free, ram_shared, ram_buffered, ram_available = [
                    int(v) for v in lines[3].split(':', 1)[1].strip().split()
                ]
                result = {
                    'timestamp': time.time(),
                    'machine': m,
                    'disk': {
                        'fs': fs,
                        'blocks_1k': blocks_1k,
                        'used': used,
                        'available': available,
                        'use_percent': use_percent,
                        'mounted_on': mounted_on,
                    },
                    'ram': {
                        'total': ram_total,
                        'used': ram_used,
                        'free': ram_free,
                        'shared': ram_shared,
                        'buffered': ram_buffered,
                        'available': ram_available,
                    }
                }

                individual_results.append(result)
    return individual_results

def continuously_collect_snapshots(interval=5*60):
    last = time.time()
    # every 60 seconds, get a snapshot, and concat all of the data so far
    full_results = []
    if not os.path.isfile('diskspace_4d_experiment.tsv'):
        with open('diskspace_4d_experiment.tsv', 'w') as f:
            f.write('\t'.join(COLUMNS+DISK_COLUMNS) + '\n')
            f.flush()
    if not os.path.isfile('memory_4d_experiment.tsv'):
        with open('memory_4d_experiment.tsv', 'w') as f:
            f.write('\t'.join(COLUMNS+RAM_COLUMNS) + '\n')
            f.flush()
    while True:
        snapshot = get_snapshot()
        full_results.append(snapshot)
        with open('diskspace_4d_experiment.tsv', 'a') as f:
            for s in snapshot:
                vals = [s[c] for c in COLUMNS] + [s['disk'][c] for c in DISK_COLUMNS]
                f.write('\t'.join(map(str, vals)) + '\n')
                f.flush()
        with open('memory_4d_experiment.tsv', 'a') as f:
            for s in snapshot:
                vals = [s[c] for c in COLUMNS] + [s['ram'][c] for c in RAM_COLUMNS]
                f.write('\t'.join(map(str, vals)) + '\n')
                f.flush()
        now = time.time()
        time_to_sleep = interval
        print('Sleeping for', time_to_sleep)
        assert time_to_sleep > 0
        last = now
        time.sleep(time_to_sleep)

if __name__ == '__main__':
    continuously_collect_snapshots()
