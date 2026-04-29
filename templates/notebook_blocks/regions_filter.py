# ##AGENT:regions_filter##
# Распределение по регионам
integrum = spark.read.table(ml360_folder.format('u_sparkinterfax_integrum'))\
                    .select('inn', 'okato_cd')\
                    .withColumn('okato', F.col('okato_cd')[0:2])
        
# okato = spark.read.parquet('okato').withColumnRenamed('okato_cd', 'okato')  

inn_wth_regions = integrum.join(F.broadcast(spark.table("arnsdpsbx_t_team_monetization_products.ens_dict_cc_region_okato")), on = 'okato', how = 'inner')


regions = $regions_repr
f_ocrygs = $f_ocrygs_repr

if len(regions) > 0 and len(f_ocrygs) > 0:
    inn_wth_regions = inn_wth_regions.filter(
        F.col('region').isin(regions) | F.col('f_ocryg').isin(f_ocrygs)
    )
elif len(regions) > 0:
    inn_wth_regions = inn_wth_regions.filter(F.col('region').isin(regions))
elif len(f_ocrygs) > 0:
    inn_wth_regions = inn_wth_regions.filter(F.col('f_ocryg').isin(f_ocrygs))
