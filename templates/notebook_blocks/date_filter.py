# ##AGENT:date_filter##
words_finadv = sbersov_table
words_finadv = words_finadv[
    (~words_finadv['c_nazn'].isNull())
    & (words_finadv['short_dt'] >= $start_date_repr)
    & (words_finadv['short_dt'] <= $end_date_repr)
]
