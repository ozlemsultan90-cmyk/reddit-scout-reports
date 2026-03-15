$posts as $posts |
$keywords as $keywords |
$media_map as $media_map |
def score_calc:
    .score as $score |
    .num_comments as $comments |
    (.upvote_ratio // 1) as $ratio |
    ( (.title + " " + (.selftext // "")) | ascii_downcase ) as $text |
    ( [ $score, 5000 ] | min / 500 ) as $raw |
    ( ($comments / ($score + 1)) * 100 * 0.03 ) as $eng |
    ( if $eng > 3 then 3 else $eng end ) as $engagement |
    ( $ratio * 10 ) as $ratio_points |
    ( $keywords | map(select($text | contains(.))) | length | if . > 3 then 3 else . end ) as $relevance |
    ( $raw + $engagement + $ratio_points + $relevance ) as $total |
    {
        viral_score: ( $total / 2.6 | round * 10 / 10 ),
        raw_points: ( ( $raw * 100 | round ) / 100 ),
        engagement_points: ( ( $engagement * 100 | round ) / 100 ),
        ratio_points: ( ( $ratio_points * 100 | round ) / 100 ),
        relevance_bonus: $relevance,
        hours_ago: ((now - (.created_utc|floor)) / 3600 | floor)
    };
$posts |
to_entries |
map(.value + {index: .key}) |
map(. + (score_calc) + {media_sources: (($media_map[ (.index|tostring) ] // []) )}) |
sort_by(.viral_score) | reverse
