import pandas as pd, numpy as np, statsmodels.formula.api as smf, warnings
warnings.filterwarnings('ignore')
df=pd.read_csv('/mnt/c/Users/Phil/zoomer/outbox/dataset.csv', parse_dates=['posted'])
df=df[df.ig_views.notna()].copy()
df['t']=(df.posted-df.posted.min()).dt.days
df['era']=pd.cut(df.t,[-1,17,30,50,200],labels=['jul','aug1','aug2','sep'])
# primary outcome: likes after >= 7 days (7d snapshot if we have it, else latest for videos older than 7 d)
df['likes7']=np.where(df.ig_likes_7d.notna(), df.ig_likes_7d, np.where(df.age_days>=7, df.ig_likes, np.nan))
df['views7']=np.where(df.ig_views_7d.notna(), df.ig_views_7d, np.where(df.age_days>=7, df.ig_views, np.nan))
d=df[df.likes7.notna()].copy()
d['log_likes']=np.log1p(d.likes7); d['log_views']=np.log1p(d.views7); d['log_fol']=np.log(d.followers_at_post.clip(lower=10))
print(f"n live={len(df)}, with 7-day outcome={len(d)}; followers {int(df.followers_at_post.min())} -> {int(df.followers_latest.max())}")
print("\n=== 1. the trend: median likes (7d) and like-rate by posting era")
g=d.groupby('era',observed=True).agg(n=('journey','size'),likes=('likes7','median'),views=('views7','median'),like_rate=('ig_like_rate','median'),followers=('followers_at_post','median'))
print(g.round(3).to_string())
print("\n=== 2. how much of the lift is just the growing audience? log(likes) ~ log(followers_at_post)")
m=smf.ols('log_likes ~ log_fol', d).fit(); print(f"  slope {m.params['log_fol']:.2f} (p={m.pvalues['log_fol']:.3f}), R2 {m.rsquared:.2f}  -> likes scale with followers^{m.params['log_fol']:.2f}")
d['resid']=m.resid   # follower-adjusted performance (log scale; +0.69 = 2x)
print("\n=== 3. follower-adjusted effects (mean residual log-likes, 95% CI, n) — univariate, NOT causal")
def grp(col, mn=4):
    out=[]
    for k,s in d.groupby(col,dropna=False):
        if len(s)<mn: continue
        m_=s.resid.mean(); se=s.resid.std(ddof=1)/np.sqrt(len(s)) if len(s)>1 else np.nan
        out.append((str(k), len(s), m_, 1.96*se))
    return out
for col in ('planet_card','plate','tier','music_family','music_rhythm','music_mode','style','cameo','cut','post_weekday','full_scale','has_creature','has_water','spot_hook'):
    rows=grp(col)
    if not rows: continue
    print(f"  {col}:")
    for k,n,m_,ci in sorted(rows,key=lambda r:-r[2]): print(f"     {k:18s} n={n:2d}  {m_:+.2f} ±{ci:.2f}  (x{np.exp(m_):.2f})")
print("\n=== 4. numeric variables: Spearman corr with follower-adjusted likes (n, rho, p)")
from scipy.stats import spearmanr
for col in ('sat','lum','contrast','dark_frac','scale_span','cards','video_s','bpm_nominal','music_bpm','music_kick','music_lock','music_fit','music_brightness_hz','music_low_share','music_high_share','music_dynamics','music_onsets_per_s','music_pulse_strength','music_flatness','music_loudness_rms','caption_len','n_hashtags','parallax_gain','post_hour'):
    s=d[[col,'resid']].dropna()
    if len(s)<10: continue
    r,p=spearmanr(s[col],s.resid); print(f"  {col:22s} n={len(s):2d} rho {r:+.2f}  p={p:.3f}")
print("\n=== 5. multivariable check: ridge on standardized features, 5-fold CV R2 vs followers-only")
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import cross_val_score, KFold
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
num=['log_fol','sat','lum','contrast','dark_frac','scale_span','cards','music_bpm','music_kick','music_brightness_hz','music_low_share','music_dynamics','music_onsets_per_s','caption_len','n_hashtags']
X=d[num].copy()
for c in ('planet_card','full_scale','has_creature','spot_hook'): X[c]=d[c].astype(float)
X=pd.concat([X,pd.get_dummies(d[['music_family','music_rhythm','tier']].fillna('na'),drop_first=True).astype(float)],axis=1)
X=X.fillna(X.median()); y=d.log_likes
kf=KFold(5,shuffle=True,random_state=0)
base=cross_val_score(make_pipeline(StandardScaler(),RidgeCV(alphas=np.logspace(-2,3,30))),d[['log_fol']],y,cv=kf,scoring='r2').mean()
full=cross_val_score(make_pipeline(StandardScaler(),RidgeCV(alphas=np.logspace(-2,3,30))),X,y,cv=kf,scoring='r2').mean()
print(f"  followers only: CV R2 {base:.2f};  followers + all features ({X.shape[1]}): CV R2 {full:.2f}   (n={len(d)})")
mdl=make_pipeline(StandardScaler(),RidgeCV(alphas=np.logspace(-2,3,30))).fit(X,y)
coef=pd.Series(mdl[-1].coef_,index=X.columns).sort_values()
print("  largest standardized coefficients:"); print(pd.concat([coef.head(6),coef.tail(6)]).round(3).to_string())
print("\n=== 6. the newest 12 posts (Phil: 'only one under 10 likes')")
print(df.sort_values('posted').tail(12)[['journey','posted','ig_views','ig_likes','ig_likes_48h','plate','music_family','music_rhythm']].to_string(index=False))
