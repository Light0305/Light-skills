# Native R gallery and reproducible built-in data, called by gallery.py.
args <- commandArgs(trailingOnly=TRUE)
pkg <- normalizePath(args[1],mustWork=TRUE); out <- args[2]
dir.create(file.path(out,'data'),recursive=TRUE,showWarnings=FALSE)
dir.create(file.path(out,'figures'),recursive=TRUE,showWarnings=FALSE)
source(file.path(pkg,'scripts/publication.R'),encoding='UTF-8')
source(file.path(pkg,'scripts/domain_plots.R'),encoding='UTF-8')
use_project_style(file.path(out,'project-style.json'))
library(ggplot2)
for(nm in c('faithful','sleep','Orange','ChickWeight','volcano','mtcars','ToothGrowth')) {
  d<-get(nm,envir=asNamespace('datasets'))
  write.csv(d,file.path(out,'data',paste0(nm,'.csv')),row.names=nm=='mtcars')
}
raw<-datasets::mtcars
features<-c('mpg','disp','hp','drat','wt','qsec','carb')
mat<-t(scale(as.matrix(raw[,features])))
metadata<-data.frame(sample=rownames(raw),Transmission=ifelse(raw$am==0,'Automatic','Manual'))
bound<-ceiling(max(abs(mat))*2)/2
ht<-annotated_heatmap_r(mat,metadata,'sample','Transmission',
  list(Transmission=lc_colors(c('Automatic','Manual'))),limits=c(-bound,bound),center=0,
  cluster_rows=TRUE,cluster_columns=TRUE,
  column_split=factor(paste0(raw$cyl,' cylinders'),levels=c('4 cylinders','6 cylinders','8 cylinders')),
  name='Row z score',show_column_names=TRUE)
draw<-function(x){grid::grid.newpage();ComplexHeatmap::draw(x,newpage=FALSE,
  padding=grid::unit(rep(5,4),'mm'),heatmap_legend_side='right',annotation_legend_side='right')}
save_figure_r(ht,file.path(out,'figures/31_R_clustered'),width_mm=180,height_mm=124,draw=draw)
write.csv(mat,file.path(out,'data/mtcars_z.csv'),row.names=TRUE)
write.csv(metadata,file.path(out,'data/mtcars_metadata.csv'),row.names=FALSE)

d<-survival::lung;d$id<-seq_len(nrow(d));d$event<-d$status-1L
d$group<-ifelse(d$sex==1,'Male','Female')
km<-survival_panel_r(d,'time','event','group','id',c(0,250,500,750,1000),
  palette=lc_colors(c('Male','Female')),time_label='Follow-up (days)',group_order=c('Male','Female'))
km$plot<-km$plot+patchwork::plot_annotation(theme=theme(plot.margin=margin(7,10,7,10)))
save_figure_r(km$plot,file.path(out,'figures/32_R_survival'),width_mm=132,height_mm=102)
write.csv(d[,c('id','time','event','group')],file.path(out,'data/lung.csv'),row.names=FALSE)
write.csv(km$curve,file.path(out,'data/lung_curve.csv'),row.names=FALSE)
write.csv(km$risk,file.path(out,'data/lung_risk.csv'),row.names=FALSE)
for(i in seq_len(nrow(km$risk)))stopifnot(km$risk$n[i]==sum(d$group==km$risk$group[i]&d$time>=km$risk$time[i]))

d<-datasets::ToothGrowth;d$record<-seq_len(nrow(d));d$dose<-factor(d$dose,levels=c(.5,1,2))
p<-ggplot(d,aes(dose,len,color=supp,shape=supp))+
  geom_point(position=position_jitter(width=.12,height=0,seed=207),size=1.65,stroke=.5)+
  stat_summary(fun=median,geom='point',shape=18,size=2.6,color='#252B32')+
  facet_wrap(~supp,nrow=1)+scale_color_manual(values=lc_colors(c('OJ','VC')))+
  scale_shape_manual(values=c(OJ=16,VC=17))+
  scale_y_continuous(limits=c(0,36),breaks=c(0,10,20,30),expand=expansion(mult=c(0,.02)))+
  labs(x='Vitamin C dose (mg/day)',y='Tooth length')+theme_light_chart()+
  theme(legend.position='none',strip.text=element_text(size=7.5),plot.background=element_rect(fill='white',colour=NA))
save_figure_r(p,file.path(out,'figures/33_R_facets'),width_mm=132,height_mm=88,
  review_plots=list(dose=p),source_files=c(raw=file.path(out,'data/ToothGrowth.csv')),
  alignment_options=list(panel_ids=c('OJ','VC'),row_groups=list(c('OJ','VC')),column_groups=list()))
jsonlite::write_json(list(backend='native R',heatmap_dim=dim(mat),
  lung_n=nrow(survival::lung),risk_verified=TRUE,facet_points=nrow(d)),
  file.path(out,'R-checks.json'),auto_unbox=TRUE,pretty=TRUE)
cat('NATIVE_GALLERY_COMPLETE\n')
