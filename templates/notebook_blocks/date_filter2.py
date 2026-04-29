# ##AGENT:date_filter2##
words_finadv_upd = sbersov_table
words_finadv_upd_ = words_finadv_upd[
    (~words_finadv_upd['c_nazn'].isNull())
    & (words_finadv_upd['short_dt'] >= $start_date_repr)
    & (words_finadv_upd['short_dt'] <= $end_date_repr)
]
