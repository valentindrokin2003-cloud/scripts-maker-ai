# ##AGENT:revenue##
# Выручка
revenue = spark.read.table(ml360_folder.format('yr_fin_statement'))\
                   .withColumn('revenue', F.col('fin_stmt_2110_amt')*1000).select('inn', 'revenue', 'yr')

partition = Window.partitionBy('inn').orderBy(F.col('yr').desc())

revenue_2022_2023 = revenue.withColumn('rn', F.row_number().over(partition))\
                     .select('inn', 'revenue', 'yr', 'rn')\
                     .filter(F.col('rn') == 1)\
                     .filter(F.col('yr')[0:4] > '2022')\
                     .withColumnRenamed('yr', 'year_revenue')\
                     .drop('rn')

start_rev = $revenue_min
$revenue_filter_block
