args<-commandArgs(trailingOnly=TRUE)
mode<-args[1];pkg<-normalizePath(args[2],mustWork=TRUE);out<-args[3]
dir.create(out,recursive=TRUE,showWarnings=FALSE)
if(mode=='data') {
  write.csv(datasets::ChickWeight,file.path(out,'ChickWeight.csv'),row.names=FALSE)
  write.csv(datasets::CO2,file.path(out,'CO2.csv'),row.names=FALSE)
  write.table(datasets::volcano,file.path(out,'volcano.csv'),sep=',',row.names=FALSE,col.names=FALSE)
  helpfile<-utils:::.getHelpFile(help('volcano',package='datasets'))
  writeLines(capture.output(tools::Rd2txt(helpfile)),file.path(out,'volcano-source.txt'))
  cat('NEW_DATA_EXPORTED\n')
} else {
  library(ggplot2);library(patchwork)
  source(file.path(pkg,'scripts/publication.R'),encoding='UTF-8')
  d<-read.csv(file.path(out,'CO2.csv'));d$Plant<-factor(d$Plant)
  d$series<-paste(d$Type,d$Treatment,sep=' / ')
  endpoint<-d[d$conc==1000,];endpoint$series<-factor(endpoint$series,
    levels=c('Quebec / nonchilled','Quebec / chilled','Mississippi / nonchilled','Mississippi / chilled'))
  d$series<-factor(d$series,levels=levels(endpoint$series));groups<-levels(d$series)
  med<-aggregate(uptake~conc+series,d,median)
  write.csv(endpoint,file.path(out,'R_endpoints.csv'),row.names=FALSE)
  for(version in c('before','final','lost-layer','clipped','wrong-map')) {
    use_project_style(file.path(out,if(version=='before')'R-before-style.json' else 'CO2-style.json'))
    enc<-lc_encodings(groups);colors<-lc_colors(groups)
    types<-setNames(vapply(enc,function(x)x$linetype,character(1)),groups)
    shapes<-setNames(vapply(enc,function(x)as.integer(x$shape),integer(1)),groups)
    p<-ggplot(d,aes(conc,uptake,color=series,linetype=series))+
      geom_line(aes(group=Plant),linewidth=.35,alpha=.45)+
      geom_line(data=med,aes(group=series),linewidth=.95)+
      scale_color_manual(values=colors,drop=FALSE)+scale_linetype_manual(values=types,drop=FALSE)+
      scale_x_continuous(breaks=c(100,350,675,1000))+
      scale_y_continuous(limits=c(0,50),breaks=c(0,15,30,45),expand=expansion(mult=c(0,.02)))+
      labs(x='CO₂ concentration (µL L⁻¹)',y='Uptake (µmol m⁻² s⁻¹)')+
      guides(color=guide_legend(ncol=2),linetype=guide_legend(ncol=2))+
      theme_light_chart()+theme(plot.background=element_rect(fill='white',colour=NA),legend.position=if(version=='before')c(.55,.8) else 'top',
       legend.key.width=grid::unit(9,'mm'),legend.margin=margin(0,0,3,0))
    q<-ggplot(endpoint,aes(series,uptake,color=series,shape=series))+
      geom_point(position=position_jitter(width=.11,height=0,seed=194),size=2,stroke=.6)+
      scale_color_manual(values=colors,drop=FALSE)+scale_shape_manual(values=shapes,drop=FALSE)+
      scale_y_continuous(limits=c(0,50),breaks=c(0,15,30,45),expand=expansion(mult=c(0,.02)))+
      scale_x_discrete(labels=c('Quebec\nnonchilled','Quebec\nchilled','Mississippi\nnonchilled','Mississippi\nchilled'))+
      labs(x=NULL,y='Uptake at 1000 µL L⁻¹')+
      theme_light_chart()+theme(plot.background=element_rect(fill='white',colour=NA),legend.position='none',axis.text.x=element_text(size=7))
    if(version=='lost-layer')p$layers<-p$layers[-1]
    if(version=='clipped')p<-p+coord_cartesian(ylim=c(10,30))
    if(version=='wrong-map')p<-p+scale_color_manual(values=setNames(rev(unname(colors)),groups))
    tag_theme<-theme(plot.tag.location='panel',plot.tag.position=c(.015,.985),
      plot.tag=element_text(face='bold',size=8.5,hjust=0,vjust=1))
    p<-p+tag_theme;q<-q+tag_theme
    plots<-list(response=p,endpoint=q)
    combined<-p+q+plot_layout(widths=c(1.5,1),guides=if(version=='before')'auto' else 'collect')+
      plot_annotation(tag_levels='a',theme=theme(plot.margin=margin(3,5,3,5),legend.position='top'))
    name<-paste0('T02_R_',version)
    result<-tryCatch(save_figure_r(combined,file.path(out,name),width_mm=180,height_mm=108,
      review_plots=plots,source_files=c(CO2=file.path(out,'CO2.csv')),
      alignment_options=list(panel_ids=c('response','endpoint'),
       row_groups=list(c('response','endpoint')),column_groups=list())),error=function(e) {
         if(version %in% c('before','clipped','wrong-map'))return(list(automated_status='FAIL',error=conditionMessage(e)))
         stop(e)
       })
    cat(name,result$automated_status,'\n')
  }
  cat('NATIVE_R_REVISION_TASK_COMPLETE\n')
}
