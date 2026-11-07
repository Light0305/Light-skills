# A second native-R structure: independent records and facets, not plant paths.
args<-commandArgs(trailingOnly=TRUE);pkg<-args[1];out<-args[2]
dir.create(out,recursive=TRUE,showWarnings=FALSE)
source(file.path(pkg,'scripts/publication.R'),encoding='UTF-8')
library(ggplot2)
d<-datasets::ToothGrowth;d$record<-seq_len(nrow(d));d$dose<-factor(d$dose,levels=c(.5,1,2))
write.csv(d,file.path(out,'ToothGrowth.csv'),row.names=FALSE)
style<-jsonlite::read_json(file.path(pkg,'assets/project-style.json'),simplifyVector=TRUE)
style$groups<-list(OJ=list(color='#0072B2',shape=16L,marker='o'),VC=list(color='#B65022',shape=17L,marker='^'))
jsonlite::write_json(style,file.path(out,'ToothGrowth-style.json'),auto_unbox=TRUE,pretty=TRUE)
use_project_style(file.path(out,'ToothGrowth-style.json'))
p<-ggplot(d,aes(dose,len,color=supp,shape=supp))+
  geom_point(position=position_jitter(width=.12,height=0,seed=207),size=1.65,stroke=.5)+
  stat_summary(fun=median,geom='point',shape=18,size=2.6,color='#252B32')+
  facet_wrap(~supp,nrow=1)+scale_color_manual(values=lc_colors(c('OJ','VC')))+
  scale_shape_manual(values=c(OJ=16,VC=17))+
  scale_y_continuous(limits=c(0,36),breaks=c(0,10,20,30),expand=expansion(mult=c(0,.02)))+
  labs(x='Vitamin C dose (mg/day)',y='Tooth length')+theme_light_chart()+
  theme(legend.position='none',strip.text=element_text(size=7.5),
    plot.background=element_rect(fill='white',colour=NA))
qa<-save_figure_r(p,file.path(out,'T06_R_holdout'),width_mm=132,height_mm=88,
  review_plots=list(dose=p),source_files=c(raw=file.path(out,'ToothGrowth.csv')),
  alignment_options=list(panel_ids=c('OJ','VC'),row_groups=list(c('OJ','VC')),column_groups=list()))
stopifnot(nrow(d)==60,all(table(d$supp,d$dose)==10),qa$automated_status=='PASS')
jsonlite::write_json(list(rows=60,cells=6,per_cell=10,raw_points=60,median_marks=6,
  facet_snapshots=names(qa$figure_snapshot$panels),backend='native R',table_verified=TRUE),
  file.path(out,'T06_checks.json'),auto_unbox=TRUE,pretty=TRUE)
writeLines(c('R datasets::ToothGrowth: 60 guinea pigs, two delivery methods, three doses, ten animals per cell.',
 'All 60 raw observations are shown, with deterministic horizontal display jitter and unchanged tooth length.',
 'Black diamonds are within-cell medians. Facets preserve the supplement identities OJ and VC.',
 'Dose is categorical in this display; no fitted response, interval or significance claim is invented.',
 'The source documentation does not state a tooth-length unit, so none is inferred.'),
 file.path(out,'T06_R_holdout.caption.md'))
cat('HELD_OUT_R_FACETS_COMPLETE\n')
