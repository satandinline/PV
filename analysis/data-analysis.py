"""
Patent Data Analysis Script
===========================
This script performs descriptive statistics and visualization on patent data.
Output files are organized into:
  - visualization/ : Charts and graphs
  - statistics/    : Descriptive statistics charts
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import os
import warnings
warnings.filterwarnings('ignore')

# ========== Setup ==========
# Base paths
BASE_DIR = 'd:/git/mygit/PV'
DATA_DIR = BASE_DIR
VIS_DIR = os.path.join(BASE_DIR, 'analysis', 'visualization')
STAT_DIR = os.path.join(BASE_DIR, 'analysis', 'statistics')

# Create directories if not exist
os.makedirs(VIS_DIR, exist_ok=True)
os.makedirs(STAT_DIR, exist_ok=True)

# Configure font
matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'KaiTi', 'STKaiti', 'FangSong']
matplotlib.rcParams['axes.unicode_minus'] = False

print('=' * 70)
print('PATENT DATA ANALYSIS')
print('=' * 70)
print(f'Data directory: {DATA_DIR}')
print(f'Visualization output: {VIS_DIR}')
print(f'Statistics output: {STAT_DIR}')

# ========== Data Loading & Preprocessing ==========
print('\n[1] Loading and Preprocessing Data...')
df = pd.read_csv(f'{DATA_DIR}/data.csv', encoding='utf-8')
print(f'Raw data: {df.shape[0]} rows x {df.shape[1]} cols')

# Filter header rows
df = df[df['专利类型'] != '专利类型'].copy()
print(f'After filtering: {len(df)} records')

# Convert numeric columns
df['引用5年'] = pd.to_numeric(df['5年内被引用数量'], errors='coerce')
df['引用3年'] = pd.to_numeric(df['3年内被引用数量'], errors='coerce')
df['同族数量'] = pd.to_numeric(df['Patsnap同族专利申请数量'], errors='coerce')

# Convert date column
df['申请年份'] = pd.to_datetime(df['申请日'], errors='coerce').dt.year

# Classify legal status
def classify_legal(status):
    if pd.isna(status):
        return 'Unknown'
    s = str(status)
    if '授权' in s:
        return 'Granted'
    elif '实质审查' in s:
        return 'Examination'
    elif '驳回' in s:
        return 'Rejected'
    elif '撤回' in s:
        return 'Withdrawn'
    elif '未缴年费' in s:
        return 'Lapsed'
    elif '公开' in s:
        return 'Published'
    else:
        return 'Other'

df['法律状态分类'] = df['法律状态/事件'].apply(classify_legal)

print('Preprocessing complete.')

# ========== Descriptive Statistics ==========
print('\n[2] Generating Descriptive Statistics...')

# 2.1 Column Info Table
fig, ax = plt.subplots(figsize=(14, 10))
ax.axis('off')
info_list = []
for col in df.columns:
    info_list.append({
        'Column': col[:20],
        'Type': str(df[col].dtype)[:10],
        'Non-null': df[col].notna().sum(),
        'Non-null%': f"{df[col].notna().sum() / len(df) * 100:.1f}%",
        'Unique': df[col].nunique()
    })
info_df = pd.DataFrame(info_list)
table = ax.table(cellText=info_df.values, colLabels=info_df.columns, loc='upper center',
                 cellLoc='center', colColours=['#3498db']*5)
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1.2, 1.5)
for (row, col), cell in table.get_celld().items():
    if row == 0:
        cell.set_text_props(fontweight='bold', color='white')
    cell.set_edgecolor('white')
ax.set_title('Column Information Overview', fontsize=14, fontweight='bold', pad=50)
plt.tight_layout()
plt.savefig(f'{STAT_DIR}/01_column_info.png', dpi=100, bbox_inches='tight', facecolor='white')
plt.close()
print(f'  Saved: 01_column_info.png')

# 2.2 Numeric Statistics Summary
fig, ax = plt.subplots(figsize=(10, 5))
ax.axis('off')
numeric_cols = ['引用5年', '引用3年', '同族数量']
numeric_stats = df[numeric_cols].describe().T
numeric_stats['Missing'] = len(df) - df[numeric_cols].count()
table = ax.table(cellText=numeric_stats.round(2).values,
                 colLabels=numeric_stats.columns,
                 rowLabels=numeric_stats.index,
                 loc='center', cellLoc='center',
                 colColours=['#2ecc71']*len(numeric_stats.columns))
table.auto_set_font_size(False)
table.set_fontsize(11)
table.scale(1.3, 2)
for (row, col), cell in table.get_celld().items():
    if row == 0:
        cell.set_text_props(fontweight='bold', color='white')
    cell.set_edgecolor('white')
ax.set_title('Numeric Fields Descriptive Statistics', fontsize=14, fontweight='bold', pad=20)
plt.tight_layout()
plt.savefig(f'{STAT_DIR}/02_numeric_stats.png', dpi=100, bbox_inches='tight', facecolor='white')
plt.close()
print(f'  Saved: 02_numeric_stats.png')

# 2.3 Text Field Character Length
fig, ax = plt.subplots(figsize=(10, 5))
ax.axis('off')
text_cols = ['标题', '摘要', 'IPC主分类号(小类)']
text_stats = df[text_cols].astype(str).apply(lambda x: x.str.len()).describe().T
table = ax.table(cellText=text_stats.round(2).values,
                 colLabels=text_stats.columns,
                 rowLabels=text_stats.index,
                 loc='center', cellLoc='center',
                 colColours=['#9b59b6']*len(text_stats.columns))
table.auto_set_font_size(False)
table.set_fontsize(11)
table.scale(1.3, 2)
for (row, col), cell in table.get_celld().items():
    if row == 0:
        cell.set_text_props(fontweight='bold', color='white')
    cell.set_edgecolor('white')
ax.set_title('Text Field Character Length Statistics', fontsize=14, fontweight='bold', pad=20)
plt.tight_layout()
plt.savefig(f'{STAT_DIR}/03_text_length_stats.png', dpi=100, bbox_inches='tight', facecolor='white')
plt.close()
print(f'  Saved: 03_text_length_stats.png')

# 2.4 Legal Status Classification Summary
fig, ax = plt.subplots(figsize=(10, 5))
ax.axis('off')
legal_counts = df['法律状态分类'].value_counts()
legal_df = pd.DataFrame({'Status': legal_counts.index, 'Count': legal_counts.values, 
                         'Percentage': (legal_counts.values / len(df) * 100).round(2)})
table = ax.table(cellText=legal_df.values,
                 colLabels=legal_df.columns,
                 loc='center', cellLoc='center',
                 colColours=['#e74c3c']*len(legal_df.columns))
table.auto_set_font_size(False)
table.set_fontsize(11)
table.scale(1.3, 2)
for (row, col), cell in table.get_celld().items():
    if row == 0:
        cell.set_text_props(fontweight='bold', color='white')
    cell.set_edgecolor('white')
ax.set_title('Legal Status Classification Summary', fontsize=14, fontweight='bold', pad=20)
plt.tight_layout()
plt.savefig(f'{STAT_DIR}/04_legal_status_stats.png', dpi=100, bbox_inches='tight', facecolor='white')
plt.close()
print(f'  Saved: 04_legal_status_stats.png')

# 2.5 Data Quality Summary
fig, ax = plt.subplots(figsize=(10, 4))
ax.axis('off')
quality_data = [
    ['Total Records', len(df)],
    ['Total Columns', len(df.columns)],
    ['Duplicate Rows', df.duplicated().sum()],
    ['Numeric Valid Values', df['引用5年'].notna().sum()]
]
quality_df = pd.DataFrame(quality_data, columns=['Metric', 'Value'])
table = ax.table(cellText=quality_df.values,
                 colLabels=quality_df.columns,
                 loc='center', cellLoc='center',
                 colColours=['#3498db']*2)
table.auto_set_font_size(False)
table.set_fontsize(12)
table.scale(1.2, 2)
for (row, col), cell in table.get_celld().items():
    if row == 0:
        cell.set_text_props(fontweight='bold', color='white')
    cell.set_edgecolor('white')
ax.set_title('Data Quality Summary', fontsize=14, fontweight='bold', pad=20)
plt.tight_layout()
plt.savefig(f'{STAT_DIR}/05_data_quality.png', dpi=100, bbox_inches='tight', facecolor='white')
plt.close()
print(f'  Saved: 05_data_quality.png')

# ========== Visualizations ==========
print('\n[3] Generating Visualizations...')

# 3.1 Patent Type Distribution
fig, ax = plt.subplots(figsize=(10, 6))
patent_type = df['专利类型'].value_counts()
print(f'  Patent types: {patent_type.to_dict()}')
colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12']
bars = ax.bar(range(len(patent_type)), patent_type.values, color=colors[:len(patent_type)], edgecolor='white', linewidth=1.5)
ax.set_xticks(range(len(patent_type)))
ax.set_xticklabels(patent_type.index, fontsize=12)
ax.set_xlabel('Patent Type', fontsize=13)
ax.set_ylabel('Count', fontsize=13)
ax.set_title('Patent Type Distribution', fontsize=15, fontweight='bold')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
for bar in bars:
    height = bar.get_height()
    pct = height / len(df) * 100
    ax.text(bar.get_x() + bar.get_width()/2., height + 50, f'{int(height)}\n({pct:.1f}%)', 
            ha='center', va='bottom', fontsize=11, fontweight='bold')
ax.set_ylim(0, patent_type.max() * 1.2)
plt.tight_layout()
plt.savefig(f'{VIS_DIR}/01_patent_type.png', dpi=100, bbox_inches='tight', facecolor='white')
plt.close()
print(f'  Saved: 01_patent_type.png')

# 3.2 IPC Subclass Distribution
fig, ax = plt.subplots(figsize=(12, 8))
ipc_data = df[df['IPC主分类号(小类)'] != '-']['IPC主分类号(小类)'].value_counts().head(15)
print(f'  IPC subclass top: {ipc_data.index[0]}={ipc_data.values[0]}')
colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(ipc_data)))
bars = ax.barh(range(len(ipc_data)), ipc_data.values, color=colors, edgecolor='white', linewidth=0.5)
ax.set_yticks(range(len(ipc_data)))
ax.set_yticklabels(ipc_data.index[::-1], fontsize=11)
ax.set_xlabel('Count', fontsize=13)
ax.set_ylabel('IPC Subclass', fontsize=13)
ax.set_title('IPC Subclass Distribution (Top 15)', fontsize=15, fontweight='bold')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
for i, v in enumerate(ipc_data.values[::-1]):
    ax.text(v + 20, i, str(int(v)), va='center', fontsize=10, fontweight='bold')
ax.set_xlim(0, ipc_data.max() * 1.12)
plt.tight_layout()
plt.savefig(f'{VIS_DIR}/02_ipc_subclass.png', dpi=100, bbox_inches='tight', facecolor='white')
plt.close()
print(f'  Saved: 02_ipc_subclass.png')

# 3.3 IPC Main Group Distribution
fig, ax = plt.subplots(figsize=(12, 7))
ipc_main = df[df['IPC主分类号(大组)'] != '-']['IPC主分类号(大组)'].value_counts().head(12)
colors = plt.cm.Oranges(np.linspace(0.4, 0.85, len(ipc_main)))
bars = ax.barh(range(len(ipc_main)), ipc_main.values, color=colors, edgecolor='white', linewidth=0.5)
ax.set_yticks(range(len(ipc_main)))
ax.set_yticklabels(ipc_main.index[::-1], fontsize=11)
ax.set_xlabel('Count', fontsize=13)
ax.set_ylabel('IPC Main Group', fontsize=13)
ax.set_title('IPC Main Group Distribution (Top 12)', fontsize=15, fontweight='bold')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
for i, v in enumerate(ipc_main.values[::-1]):
    ax.text(v + 15, i, str(int(v)), va='center', fontsize=10, fontweight='bold')
ax.set_xlim(0, ipc_main.max() * 1.12)
plt.tight_layout()
plt.savefig(f'{VIS_DIR}/03_ipc_main.png', dpi=100, bbox_inches='tight', facecolor='white')
plt.close()
print(f'  Saved: 03_ipc_main.png')

# 3.4 Application Year Distribution
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
yearly = df['申请年份'].dropna().value_counts().sort_index()

axes[0].bar(yearly.index.astype(int), yearly.values, color='#3498db', alpha=0.85, edgecolor='white')
axes[0].set_xlabel('Year', fontsize=12)
axes[0].set_ylabel('Count', fontsize=12)
axes[0].set_title('Application Year (All)', fontsize=13, fontweight='bold')
axes[0].tick_params(axis='x', rotation=45)
axes[0].spines['top'].set_visible(False)
axes[0].spines['right'].set_visible(False)

recent = yearly[yearly.index >= 2015]
colors = plt.cm.Reds(np.linspace(0.4, 0.9, len(recent)))
axes[1].bar(recent.index.astype(int), recent.values, color=colors, edgecolor='white', alpha=0.9)
axes[1].set_xlabel('Year', fontsize=12)
axes[1].set_ylabel('Count', fontsize=12)
axes[1].set_title('Application Year (2015-2026)', fontsize=13, fontweight='bold')
axes[1].tick_params(axis='x', rotation=45)
axes[1].spines['top'].set_visible(False)
axes[1].spines['right'].set_visible(False)
for year, val in zip(recent.index.astype(int), recent.values):
    axes[1].text(year, val + 50, str(int(val)), ha='center', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig(f'{VIS_DIR}/04_application_year.png', dpi=100, bbox_inches='tight', facecolor='white')
plt.close()
print(f'  Saved: 04_application_year.png')

# 3.5 Citation & Family Distribution
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

引用5年 = df['引用5年'].dropna()
引用5年_nonzero = 引用5年[引用5年 > 0]
axes[0].hist(引用5年_nonzero, bins=25, color='#3498db', edgecolor='white', alpha=0.85)
axes[0].axvline(引用5年.mean(), color='#e74c3c', linestyle='--', linewidth=2, label=f'Mean: {引用5年.mean():.2f}')
axes[0].axvline(引用5年.median(), color='#2ecc71', linestyle=':', linewidth=2, label=f'Median: {引用5年.median():.0f}')
axes[0].set_xlabel('Citation Count', fontsize=11)
axes[0].set_ylabel('Frequency', fontsize=11)
axes[0].set_title('Citations within 5 Years', fontsize=12, fontweight='bold')
axes[0].legend(fontsize=9)
axes[0].spines['top'].set_visible(False)
axes[0].spines['right'].set_visible(False)

引用3年 = df['引用3年'].dropna()
引用3年_nonzero = 引用3年[引用3年 > 0]
axes[1].hist(引用3年_nonzero, bins=25, color='#9b59b6', edgecolor='white', alpha=0.85)
axes[1].axvline(引用3年.mean(), color='#e74c3c', linestyle='--', linewidth=2, label=f'Mean: {引用3年.mean():.2f}')
axes[1].axvline(引用3年.median(), color='#2ecc71', linestyle=':', linewidth=2, label=f'Median: {引用3年.median():.0f}')
axes[1].set_xlabel('Citation Count', fontsize=11)
axes[1].set_ylabel('Frequency', fontsize=11)
axes[1].set_title('Citations within 3 Years', fontsize=12, fontweight='bold')
axes[1].legend(fontsize=9)
axes[1].spines['top'].set_visible(False)
axes[1].spines['right'].set_visible(False)

同族 = df['同族数量'].dropna()
同族_nonzero = 同族[同族 > 1]
axes[2].hist(同族_nonzero, bins=25, color='#2ecc71', edgecolor='white', alpha=0.85)
axes[2].axvline(同族.mean(), color='#e74c3c', linestyle='--', linewidth=2, label=f'Mean: {同族.mean():.2f}')
axes[2].axvline(同族.median(), color='#3498db', linestyle=':', linewidth=2, label=f'Median: {同族.median():.0f}')
axes[2].set_xlabel('Family Count', fontsize=11)
axes[2].set_ylabel('Frequency', fontsize=11)
axes[2].set_title('Patent Family Size (>1)', fontsize=12, fontweight='bold')
axes[2].legend(fontsize=9)
axes[2].spines['top'].set_visible(False)
axes[2].spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig(f'{VIS_DIR}/05_citation_family.png', dpi=100, bbox_inches='tight', facecolor='white')
plt.close()
print(f'  Saved: 05_citation_family.png')

# 3.6 Legal Status Distribution
fig, ax = plt.subplots(figsize=(10, 6))
legal = df['法律状态分类'].value_counts()
color_map = {'Granted': '#2ecc71', 'Examination': '#3498db', 'Rejected': '#e74c3c',
             'Withdrawn': '#f39c12', 'Lapsed': '#9b59b6', 'Published': '#1abc9c', 'Other': '#95a5a6'}
colors = [color_map.get(x, '#3498db') for x in legal.index]
bars = ax.bar(range(len(legal)), legal.values, color=colors, edgecolor='white', linewidth=1.5)
ax.set_xticks(range(len(legal)))
ax.set_xticklabels([f'{idx}\n({legal[idx]/len(df)*100:.1f}%)' for idx in legal.index], fontsize=11)
ax.set_xlabel('Legal Status', fontsize=13)
ax.set_ylabel('Count', fontsize=13)
ax.set_title('Legal Status Distribution (Merged Categories)', fontsize=14, fontweight='bold')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 50, f'{int(height)}', ha='center', va='bottom', fontsize=11, fontweight='bold')
ax.set_ylim(0, legal.max() * 1.15)
plt.tight_layout()
plt.savefig(f'{VIS_DIR}/06_legal_status.png', dpi=100, bbox_inches='tight', facecolor='white')
plt.close()
print(f'  Saved: 06_legal_status.png')

# 3.7 Province Distribution
fig, ax = plt.subplots(figsize=(12, 7))
province_data = df[df['当前申请(专利权)人州/省'] != '-']['当前申请(专利权)人州/省'].value_counts().head(12)
colors = plt.cm.Greens(np.linspace(0.35, 0.85, len(province_data)))
bars = ax.barh(range(len(province_data)), province_data.values, color=colors, edgecolor='white', linewidth=0.5)
ax.set_yticks(range(len(province_data)))
ax.set_yticklabels(province_data.index[::-1], fontsize=11)
ax.set_xlabel('Count', fontsize=13)
ax.set_ylabel('Province', fontsize=13)
ax.set_title('Applicant Province Distribution (Top 12)', fontsize=15, fontweight='bold')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
for i, v in enumerate(province_data.values[::-1]):
    pct = v / len(df) * 100
    ax.text(v + 20, i, f'{int(v)} ({pct:.1f}%)', va='center', fontsize=10, fontweight='bold')
ax.set_xlim(0, province_data.max() * 1.18)
plt.tight_layout()
plt.savefig(f'{VIS_DIR}/07_province.png', dpi=100, bbox_inches='tight', facecolor='white')
plt.close()
print(f'  Saved: 07_province.png')

# 3.8 Dashboard
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

patent_type = df['专利类型'].value_counts()
colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12']
axes[0, 0].pie(patent_type.values, labels=patent_type.index, autopct='%1.1f%%', 
               colors=colors, startangle=90, explode=[0.03]*len(patent_type))
axes[0, 0].set_title('Patent Type', fontsize=12, fontweight='bold')

legal = df['法律状态分类'].value_counts()
colors = [color_map.get(x, '#3498db') for x in legal.index]
axes[0, 1].bar(range(len(legal)), legal.values, color=colors)
axes[0, 1].set_xticks(range(len(legal)))
axes[0, 1].set_xticklabels(legal.index, rotation=30, ha='right', fontsize=9)
axes[0, 1].set_title('Legal Status (Merged)', fontsize=12, fontweight='bold')
axes[0, 1].spines['top'].set_visible(False)
axes[0, 1].spines['right'].set_visible(False)

yearly = df['申请年份'].dropna().value_counts().sort_index()
recent = yearly[yearly.index >= 2015]
axes[1, 0].fill_between(recent.index.astype(int), recent.values, alpha=0.3, color='#3498db')
axes[1, 0].plot(recent.index.astype(int), recent.values, marker='o', color='#3498db', linewidth=2)
axes[1, 0].set_xlabel('Year')
axes[1, 0].set_ylabel('Count')
axes[1, 0].set_title('Application Trend (2015-2026)', fontsize=12, fontweight='bold')
axes[1, 0].spines['top'].set_visible(False)
axes[1, 0].spines['right'].set_visible(False)

province = df[df['当前申请(专利权)人州/省'] != '-']['当前申请(专利权)人州/省'].value_counts().head(5)
bars = axes[1, 1].barh(range(len(province)), province.values, color='#2ecc71')
axes[1, 1].set_yticks(range(len(province)))
axes[1, 1].set_yticklabels(province.index[::-1])
axes[1, 1].set_title('Top 5 Provinces', fontsize=12, fontweight='bold')
axes[1, 1].spines['top'].set_visible(False)
axes[1, 1].spines['right'].set_visible(False)

plt.suptitle('Data Overview Dashboard', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(f'{VIS_DIR}/08_dashboard.png', dpi=100, bbox_inches='tight', facecolor='white')
plt.close()
print(f'  Saved: 08_dashboard.png')

# ========== Summary ==========
print('\n' + '=' * 70)
print('ANALYSIS COMPLETE!')
print('=' * 70)
print(f'\nStatistics charts saved to: {STAT_DIR}/')
print(f'Visualization charts saved to: {VIS_DIR}/')
print('\nFiles generated:')
print('  [Statistics]')
print('    01_column_info.png')
print('    02_numeric_stats.png')
print('    03_text_length_stats.png')
print('    04_legal_status_stats.png')
print('    05_data_quality.png')
print('  [Visualization]')
print('    01_patent_type.png')
print('    02_ipc_subclass.png')
print('    03_ipc_main.png')
print('    04_application_year.png')
print('    05_citation_family.png')
print('    06_legal_status.png')
print('    07_province.png')
print('    08_dashboard.png')
print('=' * 70)