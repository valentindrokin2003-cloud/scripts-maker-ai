# ##AGENT:okved_list##
okved_list = $okved_list_repr
okved_ = okved_part\
$okved_filter_line
    .drop_duplicates(subset=['inn'])\
    .select('inn', 'okved')
