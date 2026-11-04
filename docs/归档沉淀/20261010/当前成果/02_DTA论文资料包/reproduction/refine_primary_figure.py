"""Layout-only revision of the newly created F1; source values are unchanged."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path(__file__).resolve().parent.parent
pairing=pd.read_csv(OUT/'tables/T1_primary_seed_pairs.csv')
summary=pd.read_csv(OUT/'tables/T2_primary_effect_intervals.csv')
with plt.rc_context({'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':12,
                     'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'}):
    fig,axes=plt.subplots(1,2,figsize=(11.2,4.5),layout='constrained',gridspec_kw={'width_ratios':[1.15,1]})
    ax=axes[0]
    for row in pairing.itertuples():
        ax.plot([0,1],[row.ci_design_a,row.ci_design_d],color='#AAAAAA',linewidth=1,zorder=1)
    ax.scatter(np.zeros(5),pairing.ci_design_a,color='#D55E00',marker='s',s=50,label='A: pair random 5-fold',zorder=2)
    ax.scatter(np.ones(5),pairing.ci_design_d,color='#0072B2',marker='o',s=50,label='D: entity grid 25-block',zorder=2)
    for label_y,row in zip(np.linspace(.57,.75,5),pairing.sort_values('ci_design_d').itertuples()):
        ax.annotate(str(row.seed),(1,row.ci_design_d),xytext=(1.20,label_y),textcoords='data',
            fontsize=8,va='center',arrowprops={'arrowstyle':'-','color':'#AAAAAA','lw':.6})
    ax.set(xlim=(-.25,1.55),ylim=(0,1),xticks=[0,1],xticklabels=['Design A','Design D'],ylabel='Concordance index',title='A  Paired seed realizations')
    ax.legend(loc='lower left',fontsize=8)
    ax=axes[1]
    ax.axvline(0,color='#777777',linestyle='--',linewidth=1)
    for i,row in summary.iterrows():
        ax.errorbar(row.delta,1-i,xerr=np.array([[row.delta-row.interval_low],[row.interval_high-row.delta]]),color='#333333',marker='o',capsize=5,linewidth=2)
        ax.text(.177,1-i,f'{row.delta:+.4f}',ha='right',va='bottom',fontsize=9)
    ax.set(yticks=[1,0],yticklabels=['All pairs (n=975)','pKd > 5 (n=263)'],ylim=(-.5,1.5),xlim=(-.035,.185),xlabel='Mean paired CI difference (D minus A)',title='B  Descriptive entity-bootstrap intervals')
    fig.suptitle('Primary comparison on the same dual-cold domain | five seeds',fontsize=13)
    fig.savefig(OUT/'figures/F1_primary_comparison.png',dpi=300,facecolor='white')
    fig.savefig(OUT/'figures/F1_primary_comparison.svg',facecolor='white')
    plt.close(fig)
print('F1 layout refined: labels separated, data unchanged.')
