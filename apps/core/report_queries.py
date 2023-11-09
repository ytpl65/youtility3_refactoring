def get_query(query):
    return {
        "TaskSummary": 
            '''
            WITH timezone_setting AS (
                SELECT %s::text AS timezone
            )

            SELECT * , 
                coalesce(round(x."Total Completed"::numeric/nullif(x."Total Scheduled"::numeric,0)*100,2),0) as "Percentage"
            FROM (
                SELECT
                bu.id,
                bu.buname as Site,
                (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE as "Planned Date",
                count(jobneed.id)::numeric as "Total Tasks",
                count(case when jobneed.jobtype = 'SCHEDULE' then jobneed.jobtype end)::numeric as "Total Scheduled",
                count(case when jobneed.jobtype = 'ADHOC' then jobneed.jobtype end)::numeric as "Total Adhoc",
                count(case when jobneed.jobtype = 'SCHEDULE' and jobneed.jobstatus = 'ASSIGNED' then jobneed.jobstatus end)::numeric as "Total Pending",
                count(case when jobneed.jobtype = 'SCHEDULE' and jobneed.jobstatus = 'AUTOCLOSED' then jobneed.jobstatus end)::numeric as "Total Closed",
                count(case when jobneed.jobtype = 'SCHEDULE' and jobneed.jobstatus = 'COMPLETED' then jobneed.jobstatus end)::numeric as "Total Completed",
                count(jobneed.id)::numeric - count(case when jobneed.jobtype = 'SCHEDULE' and jobneed.jobstatus = 'COMPLETED' then jobneed.jobstatus end)::numeric as "Not Performed"
                FROM jobneed
                INNER JOIN bt bu ON bu.id=jobneed.bu_id
                CROSS JOIN timezone_setting tz
                WHERE
                jobneed.identifier='TASK' AND
                jobneed.id <> 1 AND
                bu.id <> 1 AND
                jobneed.bu_id IN (SELECT unnest(string_to_array(%s, ',')::integer[]))  AND
                (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE BETWEEN %s AND %s
                GROUP BY bu.id, bu.buname, (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE
                ORDER BY bu.buname, (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE desc
            ) as x
            '''
    }.get(query)