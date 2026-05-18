paste avg-num-floods-by-month.total.tsv avg-num-floods-by-month.minor.tsv avg-num-floods-by-month.moderate.tsv avg-num-floods-by-month.major.tsv | awk 'BEGIN{FS=OFS="\t"}$1==$3 && $1==$5 && $1==$7 {print $1,$2,$4,$6,$8}' > avg-num-floods-by-month.tsv
awk '{gsub("\t",","); print}' avg-num-floods-by-month.tsv > avg-num-floods-by-month.csv
