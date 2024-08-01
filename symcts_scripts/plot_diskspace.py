import os
import matplotlib.pyplot as plt
import pandas as pd

MACHINES = (
    'fuzzbench1', 'fuzzbench2', 'fuzzbench3', 'webster',
    'fuzzbench5', 'wood', 'fuzzbench7', 'fuzzbench8',
    'fuzzbench9', 'fuzzbench10', 'fuzzbench11'
)

df = pd.read_csv('./diskspace_4d_experiment.tsv', sep='\t')

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
ax.set_title('Disk Use Percent Over Time (4d)')
os.makedirs('/tmp/fuzzbench', exist_ok=True)
plt.savefig('/tmp/fuzzbench/diskspace_4d_experiment.svg')
# plt.show()

df_ram = pd.read_csv('./memory_4d_experiment.tsv', sep='\t')
df_ram['timestamp'] = df_ram['timestamp'].map(int)
df_ram['timestamp'] = (df_ram['timestamp'] - df_ram['timestamp'].min())
df_ram['avail_percent'] = (df_ram['used'] / df_ram['total']) * 100
fig, ax = plt.subplots()
for m in MACHINES:
    df_ram[df_ram['machine'] == m].plot(x='timestamp', y='avail_percent', ax=ax, label=m)
ax.legend(loc='lower left')
ax.set_ylabel('Used Memory')
ax.set_xlabel('Timestamp')
ax.set_title('Memory Use Percent Over Time (4d)')
os.makedirs('/tmp/fuzzbench', exist_ok=True)
plt.savefig('/tmp/fuzzbench/memory_4d_experiment.svg')
# plt.show()

MACHINES = (
    'fuzzbench2d_1', 'fuzzbench2d_2', 'fuzzbench2d_3', 'fuzzbench2d_4',
    'fuzzbench2d_5', 'fuzzbench2d_6', 'fuzzbench2d_7', 'fuzzbench2d_8',
    'fuzzbench2d_9', 'fuzzbench2d_10', 'fuzzbench2d_11'
)

df = pd.read_csv('./diskspace_2d_experiment.tsv', sep='\t')

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
ax.set_title('Disk Use Percent Over Time (2d)')
os.makedirs('/tmp/fuzzbench', exist_ok=True)
plt.savefig('/tmp/fuzzbench/diskspace_2d_experiment.svg')


df_ram = pd.read_csv('./memory_2d_experiment.tsv', sep='\t')
df_ram['timestamp'] = df_ram['timestamp'].map(int)
df_ram['timestamp'] = (df_ram['timestamp'] - df_ram['timestamp'].min())
df_ram['avail_percent'] = (df_ram['used'] / df_ram['total']) * 100
fig, ax = plt.subplots()
for m in MACHINES:
    df_ram[df_ram['machine'] == m].plot(x='timestamp', y='avail_percent', ax=ax, label=m)
ax.legend(loc='lower left')
ax.set_ylabel('Used Memory')
ax.set_xlabel('Timestamp')
ax.set_title('Memory Use Percent Over Time (2d)')
os.makedirs('/tmp/fuzzbench', exist_ok=True)
plt.savefig('/tmp/fuzzbench/memory_2d_experiment.svg')
# plt.show()