# Native R acceptance examples with bundled, named datasets. No invented outcomes.
args <- commandArgs(trailingOnly = TRUE)
script_arg <- grep("^--file=", commandArgs(), value=TRUE)
this_file <- if(length(script_arg)) sub("^--file=", "", script_arg[[1]]) else sys.frame(1)$ofile
package_root <- normalizePath(file.path(dirname(this_file), "../.."), mustWork=TRUE)
source(file.path(package_root,"scripts/publication.R"),encoding="UTF-8")
source(file.path(package_root,"scripts/domain_plots.R"),encoding="UTF-8")
out <- if(length(args)) args[[1]] else "domain-figures"
dir.create(out,recursive=TRUE,showWarnings=FALSE)

# All 32 cars, seven measured variables. Scaling is explicitly part of this demo,
# not an operation hidden inside annotated_heatmap_r().
raw <- datasets::mtcars
features <- c("mpg","disp","hp","drat","wt","qsec","carb")
mat <- t(scale(as.matrix(raw[,features]), center=TRUE, scale=TRUE))
metadata <- data.frame(sample=rownames(raw),Cylinders=paste0(raw$cyl," cylinders"),
  Transmission=ifelse(raw$am==0,"Automatic","Manual"),stringsAsFactors=FALSE)
metadata <- metadata[rev(seq_len(nrow(metadata))),] # Deliberately reorder input metadata.
pal <- list(Cylinders=c("4 cylinders"="#6F9F9A","6 cylinders"="#B8A58E","8 cylinders"="#7B82A5"),
  Transmission=c(Automatic="#C4CBD1",Manual="#465F77"))
bound <- ceiling(max(abs(mat))*2)/2
ht <- annotated_heatmap_r(mat,metadata,"sample","Transmission",pal["Transmission"],
  limits=c(-bound,bound),center=0,cluster_rows=TRUE,cluster_columns=TRUE,
  column_split=factor(paste0(raw$cyl," cylinders"),levels=c("4 cylinders","6 cylinders","8 cylinders")),
  name="Row z score",show_column_names=TRUE,font_size=7)
draw_heatmap <- function(object) {
  grid::grid.newpage()
  ComplexHeatmap::draw(object,newpage=FALSE,heatmap_legend_side="right",annotation_legend_side="right",
    padding=grid::unit(rep(4,4),"mm"))
}
save_figure_r(ht,file.path(out,"05_native_R_annotated_heatmap"),width_mm=180,height_mm=114,dpi=400,draw=draw_heatmap)
utils::write.csv(raw,file.path(out,"mtcars_source.csv"),row.names=TRUE)
utils::write.csv(mat,file.path(out,"mtcars_plotted_z_scores.csv"),row.names=TRUE)
utils::write.csv(metadata,file.path(out,"mtcars_metadata.csv"),row.names=FALSE)

# NCCTG lung cancer data from survival. This is a descriptive example, not an
# adjusted comparison, efficacy claim, randomized trial or clinical advice.
lung <- survival::lung
lung$subject <- seq_len(nrow(lung))
lung$event01 <- lung$status-1L # Original dataset: 1=censored, 2=dead.
lung$Sex <- ifelse(lung$sex==1,"Male","Female")
pal <- c(Male="#356D91",Female="#C17C65")
clinical <- survival_panel_r(lung,"time","event01","Sex","subject",c(0,250,500,750,1000),
  palette=pal,time_label="Follow-up (days)",group_order=c("Male","Female"))
clinical$plot <- clinical$plot + patchwork::plot_annotation(
  theme=ggplot2::theme(plot.margin=ggplot2::margin(7,10,7,10)))
save_figure_r(clinical$plot,file.path(out,"06_native_R_survival_risk"),width_mm=132,height_mm=102,dpi=400)
utils::write.csv(lung[,c("subject","time","status","event01","Sex")],file.path(out,"lung_source.csv"),row.names=FALSE)
utils::write.csv(clinical$risk,file.path(out,"lung_risk_counts.csv"),row.names=FALSE)
utils::write.csv(clinical$curve,file.path(out,"lung_KM_values.csv"),row.names=FALSE)
jsonlite::write_json(list(heatmap=list(source="R datasets::mtcars",n=32,features=features,
  transformation="Column mean and sample SD scaling in original data; transposed into heatmap rows",
  clustering="Euclidean / complete, columns clustered within cylinder splits",missing=0),
  survival=list(source="R survival::lung (NCCTG advanced lung cancer)",n=clinical$n,
    events=clinical$events,excluded=0,definitions=clinical$definitions,
    inference="Descriptive example only; no treatment effect or adjusted/causal inference")),
  file.path(out,"R_sources_and_definitions.json"),pretty=TRUE,auto_unbox=TRUE)
writeLines(c(
  "# Captions (outside the figure files)", "",
  "**05. Vehicle profiles (builtin data demonstration).** All 32 cars and seven measured variables from datasets::mtcars are retained. Each variable is standardized by its mean and sample SD, then transposed to a row. Euclidean/complete clustering is applied to rows and within cylinder splits. Cylinder identity is encoded by split headings; transmission is an ID-matched annotation track. No unreported measurements are imputed.", "",
  "**06. Observed survival by sex (descriptive example).** All 228 subjects from survival::lung are retained. Source status 1 (censored) / 2 (death) is explicitly converted to event 0/1. Lines: Kaplan-Meier estimates; bands: 95% log-log Greenwood confidence intervals; plus signs: censoring. Risk counts are immediately before each tick, from the same subjects. Groups are not randomized; no treatment, adjusted effect, causal claim or hypothesis test is supplied."
),file.path(out,"R_figure_captions.md"),useBytes=TRUE)
writeLines("Native R domain exports completed")
