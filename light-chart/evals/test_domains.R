# Hand-checkable survival values, ties, censoring, risk counts and rejection cases.
source("skills/light-chart/scripts/domain_plots.R",encoding="UTF-8")
expect_error <- function(code) {
  caught <- tryCatch({ force(code); FALSE },error=function(e) TRUE)
  stopifnot(caught)
}
d <- data.frame(id=paste0("S",1:7),time=c(1,2,2,3,1,3,4),
                event=c(1,1,0,1,0,1,0),group=c(rep("A",4),rep("B",3)))
p <- survival_panel_r(d,"time","event","group","id",c(0,2,4),
  palette=c(A="#336D99",B="#C17C65"),time_label="Time (days)")
a <- p$curve[p$curve$group=="A",]
stopifnot(abs(a$survival[a$time==1]-.75)<1e-12,
          abs(a$survival[a$time==2]-.5)<1e-12,
          a$survival[a$time==3]==0)
stopifnot(p$risk$n[p$risk$group=="A" & p$risk$time==2]==3,
          p$risk$n[p$risk$group=="B" & p$risk$time==2]==2,
          p$risk$n[p$risk$group=="B" & p$risk$time==4]==1)
# Short risk tick schedule does not remove later observations.
short <- survival_panel_r(d,"time","event","group","id",c(0,2),
  palette=c(A="#336D99",B="#C17C65"),time_label="Time (days)")
stopifnot(max(short$curve$time)==4)
bad <- d;bad$event[1]<-2
expect_error(survival_panel_r(bad,"time","event","group","id",c(0,2,4),
  palette=c(A="blue",B="orange"),time_label="Time"))
bad <- d;bad$id[2]<-bad$id[1]
expect_error(survival_panel_r(bad,"time","event","group","id",c(0,2,4),
  palette=c(A="blue",B="orange"),time_label="Time"))
bad <- d;bad$time[1]<-NA
expect_error(survival_panel_r(bad,"time","event","group","id",c(0,2,4),
  palette=c(A="blue",B="orange"),time_label="Time"))
writeLines("R data-integrity assertions: PASS")
