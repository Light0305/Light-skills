script<-sub('^--file=','',grep('^--file=',commandArgs(),value=TRUE)[1])
root<-normalizePath(file.path(dirname(script),'..'),mustWork=TRUE)
source(file.path(root,'skills/light-chart/scripts/ordination.R'))
x<-data.frame(id=c('s1','s2','s3','s4'),a=c(2,3,0,1),b=c(0,1,4,2),c=c(1,0,1,4))
m<-data.frame(id=rev(x$id),group=c('B','A','B','A'))
r<-hellinger_pca_r(x,m,'id',c('a','b','c'),'cover class','group')
stopifnot(identical(r$scores$id,x$id))
stopifnot(identical(as.character(r$scores$group),as.character(m$group[match(x$id,m$id)])))
stopifnot(max(abs(r$transformed-sqrt(as.matrix(x[2:4])/rowSums(x[2:4]))))<1e-12)
sv<-svd(scale(r$transformed,center=TRUE,scale=FALSE))
stopifnot(max(abs(r$variance-sv$d^2/sum(sv$d^2)))<1e-12)
stopifnot(max(abs(rowSums(r$transformed^2)-1))<1e-12)
expect_error<-function(expr){ok<-tryCatch({force(expr);FALSE},error=function(e)TRUE);stopifnot(ok)}
bad<-x;bad[1,2:4]<-0;expect_error(hellinger_pca_r(bad,m,'id',c('a','b','c'),'cover class'))
bad<-m;bad$id[1]<-bad$id[2];expect_error(hellinger_pca_r(x,bad,'id',c('a','b','c'),'cover class'))
bad<-x;bad$a[1]<-NA;expect_error(hellinger_pca_r(bad,m,'id',c('a','b','c'),'cover class'))
bad<-x;bad$a[1]<- -1;expect_error(hellinger_pca_r(bad,m,'id',c('a','b','c'),'cover class'))
bad<-x;bad$a<-as.complex(bad$a);bad$a[1]<-1+2i
expect_error(hellinger_pca_r(bad,m,'id',c('a','b','c'),'cover class'))
values<-c(-.45,-.44,-.39,.3)
cats<-factor(c('1','1','1','5'),levels=c('1','2','4','5'),ordered=TRUE)
packed<-ordinal_display_positions_r(values,cats,c('a','b','c','d'))
stopifnot(identical(packed$measured_y,values),identical(packed$category,as.character(cats)))
stopifnot(all(abs(packed$display_offset)<=.32),packed$category_center[4]==4)
stopifnot(length(unique(packed$display_x[1:3]))==3)
reordered<-ordinal_display_positions_r(rev(values),rev(cats),rev(c('a','b','c','d')))
stopifnot(max(abs(packed$display_x-reordered$display_x[match(packed$id,reordered$id)]))<1e-12)
# Real first-task density is a meaningful regression case for packing capacity.
fixture<-file.path(root,'artifacts/nature-backbone-rebuild/tasks/dune/analysis/site_scores.csv')
if(file.exists(fixture)) {
  real<-read.csv(fixture,colClasses=c(site_id='character'))
  real$Moisture<-factor(real$Moisture,levels=c('1','2','4','5'),ordered=TRUE)
  pos<-ordinal_display_positions_r(real$PC1,real$Moisture,real$site_id)
  stopifnot(identical(pos$measured_y,real$PC1),all(abs(pos$display_offset)<.5))
  for(g in levels(real$Moisture)) {
    idx<-which(real$Moisture==g)
    for(i in idx)for(j in idx[idx>i]) {
      if(abs(real$PC1[i]-real$PC1[j])<.07)
        stopifnot(abs(pos$display_x[i]-pos$display_x[j])>=.16-1e-10)
    }
  }
}
# Respect a resolved project font and reject an unavailable label solver.
source(file.path(root,'skills/light-chart/scripts/project_style.R'))
use_project_style(file.path(root,'artifacts/nature-backbone-rebuild/tasks/dune/styles/tol-blue.json'))
.lc_style_env$project$fonts$latin<-'Times New Roman'
.lc_style_env$project$fonts$serif<-TRUE
dummy<-list(scores=data.frame(site_id=c('a','b'),PC1=c(0,.1),PC2=c(0,.1),group=c('A','A')),variance=c(.5,.3))
p<-ordination_plot_r(dummy,'site_id','group',c(A='#4477AA'),c(A=16),label_sites=FALSE)
stopifnot(identical(p$theme$text$family,lc_fonts()$latin))
probe<-new.env(parent=globalenv())
probe$requireNamespace<-function(package,...)if(identical(package,'ggrepel'))FALSE else base::requireNamespace(package,...)
guard<-ordination_plot_r;environment(guard)<-probe
expect_error(guard(dummy,'site_id','group',c(A='#4477AA'),c(A=16)))
cat('ORDINATION_INVARIANTS_PASS\n')
