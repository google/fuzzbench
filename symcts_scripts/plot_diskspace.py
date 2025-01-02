import os
import matplotlib.pyplot as plt
import pandas as pd
import argparse

parser = argparse.ArgumentParser(description='Plot space usage over time')
parser.add_argument('name', type=str, help='Name of the experiment')
parser.add_argument('-m', '--machine', type=str, nargs='+', help='List of machines to plot')
args = parser.parse_args()

name = args.name
MACHINES = []
for machine in args.machine:
    MACHINES.extend(machine.split(','))
MACHINES = tuple(sorted(set(MACHINES)))

if not MACHINES:
    MACHINES = ('localhost')

df = pd.read_csv(f'./diskspace_{name}.tsv', sep='\t')

# make a plot of the dataframe with one line for each 'machine' entry where we plot timestamp and use_percent on the x and y axis, respectively

# first convert the timestamp into the number of seconds since the first timestamp
df['timestamp'] = df['timestamp'].map(int)
df['timestamp'] = (df['timestamp'] - df['timestamp'].min())
df['avail_percent'] = (df['used'] / (df['used'] + df['available'])) * 100
fig, ax = plt.subplots()
for m in MACHINES:
    df[df['machine'] == m].plot(x='timestamp', y='use_percent', ax=ax, label=m)
ax.legend(loc='lower left')
ax.set_ylabel('Used Disk Space')
ax.set_xlabel('Timestamp')
ax.set_title(f'Disk Use Percent Over Time ({name})')
os.makedirs('./plots/', exist_ok=True)
plt.savefig(f'./plots/diskspace_{name}.svg')


df_ram = pd.read_csv(f'./memory_{name}.tsv', sep='\t')
df_ram['timestamp'] = df_ram['timestamp'].map(int)
df_ram['timestamp'] = (df_ram['timestamp'] - df_ram['timestamp'].min())
df_ram['avail_percent'] = (df_ram['used'] / df_ram['total']) * 100
fig, ax = plt.subplots()
for m in MACHINES:
    df_ram[df_ram['machine'] == m].plot(x='timestamp', y='avail_percent', ax=ax, label=m)
ax.legend(loc='lower left')
ax.set_ylabel('Used Memory')
ax.set_xlabel('Timestamp')
ax.set_title(f'Memory Use Percent Over Time ({name})')
os.makedirs('./plots/', exist_ok=True)
plt.savefig(f'./plots/memory_{name}.svg')
# plt.show()