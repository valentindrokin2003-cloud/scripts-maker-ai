# ##AGENT:trans_thresholds##
# Фильтрация по объему/количеству закупок/продаж
trans_sum_ust_down = $trans_sum_min
trans_cnt_ust_down = $trans_cnt_min

lplat_filtered_7 = lplat_filtered_6.filter((lplat_filtered_6['trans_sum'] >= trans_sum_ust_down) & 
                                           (lplat_filtered_6['trans_cnt'] >= trans_cnt_ust_down))

# lpol_filtered_7 = lpol_filtered_6.filter((lpol_filtered_6['trans_sum'] >= trans_sum_ust_down) & 
#                                          (lpol_filtered_6['trans_cnt'] >= trans_cnt_ust_down))
