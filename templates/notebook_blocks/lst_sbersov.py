# ##AGENT:lst_sbersov##
lst_sbersov = $lst_sbersov_repr

df_sbersov_spark = spark.createDataFrame(pd.DataFrame(lst_sbersov, columns=['word']))
