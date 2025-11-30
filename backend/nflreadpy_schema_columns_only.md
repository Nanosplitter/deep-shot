# nflreadpy Column Reference (compressed)

For each loader below, this lists **only** the column names returned in the DataFrame.
Use this as a contract to avoid hallucinating non-existent columns.

## load_pbp

```python3
load_pbp(
    seasons: int | list[int] | bool | None = None,
) -> pl.DataFrame
```

play_id, game_id, old_game_id, home_team, away_team, season_type, week, posteam, posteam_type, defteam, side_of_field, yardline_100, game_date, quarter_seconds_remaining, half_seconds_remaining, game_seconds_remaining, game_half, quarter_end, drive, sp, qtr, down, goal_to_go, time, yrdln, ydstogo, ydsnet, desc, play_type, yards_gained, shotgun, no_huddle, qb_dropback, qb_kneel, qb_spike, qb_scramble, pass_length, pass_location, air_yards, yards_after_catch, run_location, run_gap, field_goal_result, kick_distance, extra_point_result, two_point_conv_result, home_timeouts_remaining, away_timeouts_remaining, timeout, timeout_team, td_team, td_player_name, td_player_id, posteam_timeouts_remaining, defteam_timeouts_remaining, total_home_score, total_away_score, posteam_score, defteam_score, score_differential, posteam_score_post, defteam_score_post, score_differential_post, no_score_prob, opp_fg_prob, opp_safety_prob, opp_td_prob, fg_prob, safety_prob, td_prob, extra_point_prob, two_point_conversion_prob, ep, epa, total_home_epa, total_away_epa, total_home_rush_epa, total_away_rush_epa, total_home_pass_epa, total_away_pass_epa, air_epa, yac_epa, comp_air_epa, comp_yac_epa, total_home_comp_air_epa, total_away_comp_air_epa, total_home_comp_yac_epa, total_away_comp_yac_epa, total_home_raw_air_epa, total_away_raw_air_epa, total_home_raw_yac_epa, total_away_raw_yac_epa, wp, def_wp, home_wp, away_wp, wpa, vegas_wpa, vegas_home_wpa, home_wp_post, away_wp_post, vegas_wp, vegas_home_wp, total_home_rush_wpa, total_away_rush_wpa, total_home_pass_wpa, total_away_pass_wpa, air_wpa, yac_wpa, comp_air_wpa, comp_yac_wpa, total_home_comp_air_wpa, total_away_comp_air_wpa, total_home_comp_yac_wpa, total_away_comp_yac_wpa, total_home_raw_air_wpa, total_away_raw_air_wpa, total_home_raw_yac_wpa, total_away_raw_yac_wpa, punt_blocked, first_down_rush, first_down_pass, first_down_penalty, third_down_converted, third_down_failed, fourth_down_converted, fourth_down_failed, incomplete_pass, touchback, interception, punt_inside_twenty, punt_in_endzone, punt_out_of_bounds, punt_downed, punt_fair_catch, kickoff_inside_twenty, kickoff_in_endzone, kickoff_out_of_bounds, kickoff_downed, kickoff_fair_catch, fumble_forced, fumble_not_forced, fumble_out_of_bounds, solo_tackle, safety, penalty, tackled_for_loss, fumble_lost, own_kickoff_recovery, own_kickoff_recovery_td, qb_hit, rush_attempt, pass_attempt, sack, touchdown, pass_touchdown, rush_touchdown, return_touchdown, extra_point_attempt, two_point_attempt, field_goal_attempt, kickoff_attempt, punt_attempt, fumble, complete_pass, assist_tackle, lateral_reception, lateral_rush, lateral_return, lateral_recovery, passer_player_id, passer_player_name, passing_yards, receiver_player_id, receiver_player_name, receiving_yards, rusher_player_id, rusher_player_name, rushing_yards, lateral_receiver_player_id, lateral_receiver_player_name, lateral_receiving_yards, lateral_rusher_player_id, lateral_rusher_player_name, lateral_rushing_yards, lateral_sack_player_id, lateral_sack_player_name, interception_player_id, interception_player_name, lateral_interception_player_id, lateral_interception_player_name, punt_returner_player_id, punt_returner_player_name, lateral_punt_returner_player_id, lateral_punt_returner_player_name, kickoff_returner_player_name, kickoff_returner_player_id, lateral_kickoff_returner_player_id, lateral_kickoff_returner_player_name, punter_player_id, punter_player_name, kicker_player_name, kicker_player_id, own_kickoff_recovery_player_id, own_kickoff_recovery_player_name, blocked_player_id, blocked_player_name, tackle_for_loss_1_player_id, tackle_for_loss_1_player_name, tackle_for_loss_2_player_id, tackle_for_loss_2_player_name, qb_hit_1_player_id, qb_hit_1_player_name, qb_hit_2_player_id, qb_hit_2_player_name, forced_fumble_player_1_team, forced_fumble_player_1_player_id, forced_fumble_player_1_player_name, forced_fumble_player_2_team, forced_fumble_player_2_player_id, forced_fumble_player_2_player_name, solo_tackle_1_team, solo_tackle_2_team, solo_tackle_1_player_id, solo_tackle_2_player_id, solo_tackle_1_player_name, solo_tackle_2_player_name, assist_tackle_1_player_id, assist_tackle_1_player_name, assist_tackle_1_team, assist_tackle_2_player_id, assist_tackle_2_player_name, assist_tackle_2_team, assist_tackle_3_player_id, assist_tackle_3_player_name, assist_tackle_3_team, assist_tackle_4_player_id, assist_tackle_4_player_name, assist_tackle_4_team, tackle_with_assist, tackle_with_assist_1_player_id, tackle_with_assist_1_player_name, tackle_with_assist_1_team, tackle_with_assist_2_player_id, tackle_with_assist_2_player_name, tackle_with_assist_2_team, pass_defense_1_player_id, pass_defense_1_player_name, pass_defense_2_player_id, pass_defense_2_player_name, fumbled_1_team, fumbled_1_player_id, fumbled_1_player_name, fumbled_2_player_id, fumbled_2_player_name, fumbled_2_team, fumble_recovery_1_team, fumble_recovery_1_yards, fumble_recovery_1_player_id, fumble_recovery_1_player_name, fumble_recovery_2_team, fumble_recovery_2_yards, fumble_recovery_2_player_id, fumble_recovery_2_player_name, sack_player_id, sack_player_name, half_sack_1_player_id, half_sack_1_player_name, half_sack_2_player_id, half_sack_2_player_name, return_team, return_yards, penalty_team, penalty_player_id, penalty_player_name, penalty_yards, replay_or_challenge, replay_or_challenge_result, penalty_type, defensive_two_point_attempt, defensive_two_point_conv, defensive_extra_point_attempt, defensive_extra_point_conv, safety_player_name, safety_player_id, season, cp, cpoe, series, series_success, series_result, order_sequence, start_time, time_of_day, stadium, weather, nfl_api_id, play_clock, play_deleted, play_type_nfl, special_teams_play, st_play_type, end_clock_time, end_yard_line, fixed_drive, fixed_drive_result, drive_real_start_time, drive_play_count, drive_time_of_possession, drive_first_downs, drive_inside20, drive_ended_with_score, drive_quarter_start, drive_quarter_end, drive_yards_penalized, drive_start_transition, drive_end_transition, drive_game_clock_start, drive_game_clock_end, drive_start_yard_line, drive_end_yard_line, drive_play_id_started, drive_play_id_ended, away_score, home_score, location, result, total, spread_line, total_line, div_game, roof, surface, temp, wind, home_coach, away_coach, stadium_id, game_stadium, aborted_play, success, passer, passer_jersey_number, rusher, rusher_jersey_number, receiver, receiver_jersey_number, pass, rush, first_down, special, play, passer_id, rusher_id, receiver_id, name, jersey_number, id, fantasy_player_name, fantasy_player_id, fantasy, fantasy_id, out_of_bounds, home_opening_kickoff, qb_epa, xyac_epa, xyac_mean_yardage, xyac_median_yardage, xyac_success, xyac_fd, xpass, pass_oe

## load_player_stats

```python3
load_player_stats(
    seasons: int | list[int] | bool | None = None,
    summary_level: Literal[
        "week", "reg", "post", "reg+post"
    ] = "week",
) -> pl.DataFrame
```

NOTE: Do not use anything other than "week" for `summary_level`. It changes the columns.

player*id, player_name, player_display_name, position, position_group, headshot_url, season, week, season_type, team, opponent_team, completions, attempts, passing_yards, passing_tds, passing_interceptions, sacks_suffered, sack_yards_lost, sack_fumbles, sack_fumbles_lost, passing_air_yards, passing_yards_after_catch, passing_first_downs, passing_epa, passing_cpoe, passing_2pt_conversions, pacr, carries, rushing_yards, rushing_tds, rushing_fumbles, rushing_fumbles_lost, rushing_first_downs, rushing_epa, rushing_2pt_conversions, receptions, targets, receiving_yards, receiving_tds, receiving_fumbles, receiving_fumbles_lost, receiving_air_yards, receiving_yards_after_catch, receiving_first_downs, receiving_epa, receiving_2pt_conversions, racr, target_share, air_yards_share, wopr, special_teams_tds, def_tackles_solo, def_tackles_with_assist, def_tackle_assists, def_tackles_for_loss, def_tackles_for_loss_yards, def_fumbles_forced, def_sacks, def_sack_yards, def_qb_hits, def_interceptions, def_interception_yards, def_pass_defended, def_tds, def_fumbles, def_safeties, misc_yards, fumble_recovery_own, fumble_recovery_yards_own, fumble_recovery_opp, fumble_recovery_yards_opp, fumble_recovery_tds, penalties, penalty_yards, punt_returns, punt_return_yards, kickoff_returns, kickoff_return_yards, fg_made, fg_att, fg_missed, fg_blocked, fg_long, fg_pct, fg_made_0_19, fg_made_20_29, fg_made_30_39, fg_made_40_49, fg_made_50_59, fg_made_60*, fg*missed_0_19, fg_missed_20_29, fg_missed_30_39, fg_missed_40_49, fg_missed_50_59, fg_missed_60*, fg_made_list, fg_missed_list, fg_blocked_list, fg_made_distance, fg_missed_distance, fg_blocked_distance, pat_made, pat_att, pat_missed, pat_blocked, pat_pct, gwfg_made, gwfg_att, gwfg_missed, gwfg_blocked, gwfg_distance, fantasy_points, fantasy_points_ppr

## load_schedules

```python3
load_schedules(
    seasons: int | list[int] | bool | None = True,
) -> pl.DataFrame
```

game_id, season, game_type, week, gameday, weekday, gametime, away_team, away_score, home_team, home_score, location, result, total, overtime, old_game_id, gsis, nfl_detail_id, pfr, pff, espn, ftn, away_rest, home_rest, away_moneyline, home_moneyline, spread_line, away_spread_odds, home_spread_odds, total_line, under_odds, over_odds, div_game, roof, surface, temp, wind, away_qb_id, home_qb_id, away_qb_name, home_qb_name, away_coach, home_coach, referee, stadium_id, stadium

## load_rosters

```python3
load_rosters(
    seasons: int | list[int] | bool | None = None,
) -> pl.DataFrame
```

season, team, position, depth_chart_position, jersey_number, status, full_name, first_name, last_name, birth_date, height, weight, college, gsis_id, espn_id, sportradar_id, yahoo_id, rotowire_id, pff_id, pfr_id, fantasy_data_id, sleeper_id, years_exp, headshot_url, ngs_position, week, game_type, status_description_abbr, football_name, esb_id, gsis_it_id, smart_id, entry_year, rookie_year, draft_club, draft_number

## load_snap_counts

```python3
load_snap_counts(
    seasons: int | list[int] | bool | None = None,
) -> pl.DataFrame
```

game_id, pfr_game_id, season, game_type, week, player, pfr_player_id, position, team, opponent, offense_snaps, offense_pct, defense_snaps, defense_pct, st_snaps, st_pct

## load_nextgen_stats

```python3
load_nextgen_stats(
    seasons: int | list[int] | bool | None = None,
    stat_type: Literal[
        "passing", "receiving", "rushing"
    ] = "passing",
) -> pl.DataFrame
```

season, season_type, week, player_display_name, player_position, team_abbr, avg_time_to_throw, avg_completed_air_yards, avg_intended_air_yards, avg_air_yards_differential, aggressiveness, max_completed_air_distance, avg_air_yards_to_sticks, attempts, pass_yards, pass_touchdowns, interceptions, passer_rating, completions, completion_percentage, expected_completion_percentage, completion_percentage_above_expectation, avg_air_distance, max_air_distance, player_gsis_id, player_first_name, player_last_name, player_jersey_number, player_short_name

## load_depth_charts

```python3
load_depth_charts(
    seasons: int | list[int] | bool | None = None,
) -> pl.DataFrame
```

dt, team, player_name, espn_id, gsis_id, pos_grp_id, pos_grp, pos_id, pos_name, pos_abb, pos_slot, pos_rank

## load_trades

```python3
load_trades() -> pl.DataFrame
```

trade_id, season, trade_date, gave, received, pick_season, pick_round, pick_number, conditional, pfr_id, pfr_name

## load_contracts

```python3
load_contracts() -> pl.DataFrame
```

player, position, team, is_active, year_signed, years, value, apy, guaranteed, apy_cap_pct, inflated_value, inflated_apy, inflated_guaranteed, player_page, otc_id, gsis_id, date_of_birth, height, weight, college, draft_year, draft_round, draft_overall, draft_team, cols

## load_combine

```python3
load_combine(
    seasons: int | list[int] | bool | None = True,
) -> pl.DataFrame
```

season, draft_year, draft_team, draft_round, draft_ovr, pfr_id, cfb_id, player_name, pos, school, ht, wt, forty, bench, vertical, broad_jump, cone, shuttle
