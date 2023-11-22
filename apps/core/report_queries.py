def get_query(query):
    return {
        "TaskSummary": 
            '''WITH timezone_setting AS (
            SELECT %s::text AS timezone
        )

        SELECT *,
            coalesce(round(x."Total Completed"::numeric/nullif(x."Total Scheduled"::numeric,0)*100,2),0) as "Percentage"
        FROM (
            SELECT
                bu.buname as "Site",
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
            ''',
        "TourSummary":
            '''
            WITH timezone_setting AS (
                SELECT %s ::text AS timezone
            )

            SELECT * ,
                coalesce(round(x."Total Completed"::numeric/nullif(x."Total Tours"::numeric,0)*100,2),0) as "Percentage"
            FROM (
                SELECT
                bu.id,
                bu.buname as "Site",
                (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE as "Date",
                count(jobneed.id)::numeric as "Total Tours",
            count(case when jobneed.jobtype='SCHEDULE' then jobneed.jobtype end) as "Total Scheduled",
            count(case when jobneed.jobtype='ADHOC' then jobneed.jobtype end) as "Total Adhoc",
            count(case when jobneed.jobstatus='ASSIGNED' then jobneed.jobstatus end) as "Total Pending",
            count(case when jobneed.jobstatus='AUTOCLOSED' then jobneed.jobstatus end) as "Total Closed",
            count(case when jobneed.jobstatus='COMPLETED' then jobneed.jobstatus end) as "Total Completed"

                FROM jobneed
                INNER JOIN bt bu ON bu.id=jobneed.bu_id
                CROSS JOIN timezone_setting tz
                WHERE
                jobneed.identifier='INTERNALTOUR'
                AND jobneed.id <> 1
                AND bu.id <> 1
                AND jobneed.bu_id IN (SELECT unnest(string_to_array(%s, ',')::integer[]))  
                AND (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE BETWEEN %s AND %s
                GROUP BY bu.id, bu.buname, (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE
                ORDER BY bu.buname, (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE desc
            ) as x
            ''',
        "ListOfTasks":
            '''
            WITH timezone_setting AS (
                SELECT %s::text AS timezone
            )
                SELECT
                bu.id,
                bu.buname as "Site",
                (jobneed.plandatetime AT TIME ZONE tz.timezone) as "Planned Date Time",
            jobneed.id as jobneedid,
            jobneed.identifier,
            jobneed.jobdesc as "Description",
                case
                    when jobneed.people_id <> 1 then people.peoplename
                    when jobneed.pgroup_id <> 1 then pgroup.groupname
                    else 'NONE' end as "Assigned To",
            jobneed.people_id assignedto,
            jobneed.jobtype,
            jobneed.jobstatus as "Status",
            jobneed.asset_id,
            jobneed.performedby_id as "Performed By",
            jobneed.qset_id as qsetname,
            (jobneed.expirydatetime AT TIME ZONE tz.timezone)  as "Expired Date Time" ,
            jobneed.gracetime as "Gracetime",
            jobneed.scantype,
            jobneed.receivedonserver,
            jobneed.priority,
            (jobneed.starttime AT TIME ZONE tz.timezone) as starttime ,
            (jobneed.endtime AT TIME ZONE tz.timezone) as endtime,
            jobneed.gpslocation,
            jobneed.qset_id,
            jobneed.remarks,
            asset.assetname as "Asset",
            questionset.qsetname as "Question Set",
            people.peoplename
                FROM jobneed
                INNER JOIN bt bu ON bu.id=jobneed.bu_id
            INNER JOIN asset ON asset.id=jobneed.asset_id
            INNER JOIN questionset ON questionset.id=jobneed.qset_id
            INNER JOIN people on jobneed.people_id=people.id
            inner join pgroup on pgroup.id=jobneed.pgroup_id
                CROSS JOIN timezone_setting tz
                WHERE jobneed.identifier='TASK' --AND jobneed.jobstatus='COMPLETED'
            AND jobneed.id <> 1 and jobneed.parent_id = 1
            AND bu.id <> 1
            AND jobneed.bu_id IN (SELECT unnest(string_to_array(%s, ',')::integer[]))  
            AND (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE BETWEEN %s AND %s
            ORDER BY bu.buname, (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE desc
            
            ''',
        "ListOfTours":
            '''
            WITH timezone_setting AS (
                SELECT %s ::text AS timezone
            )
                SELECT
                bu.id,
                bu.buname as "site",
                (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE as "Planned Date Time",
            jobneed.id as jobneedid,
            jobneed.identifier,
            (jobneed.plandatetime AT TIME ZONE tz.timezone) as plandatetime,
            jobneed.jobdesc as "Description",
            case
                    when jobneed.people_id <> 1 then people.peoplename
                    when jobneed.pgroup_id <> 1 then pgroup.groupname
                    else 'NONE' end as assignedto,
            jobneed.jobtype,
            jobneed.jobstatus as "Status",
            jobneed.asset_id,
            jobneed.performedby_id as "Performed By",
            jobneed.qset_id as qsetname,
            (jobneed.expirydatetime AT TIME ZONE tz.timezone) as "Expiry Date Time",
            jobneed.gracetime,
            bu.buname as site,
            jobneed.scantype,
            jobneed.receivedonserver,
            jobneed.priority,
            (jobneed.starttime AT TIME ZONE tz.timezone) as starttime ,
            (jobneed.endtime AT TIME ZONE tz.timezone) as endtime,
            jobneed.gpslocation,
            jobneed.qset_id,
            jobneed.remarks,
            asset.assetname,
            questionset.qsetname as "Question Set",
            people.peoplename
                FROM jobneed
                INNER JOIN bt bu ON bu.id=jobneed.bu_id
            INNER JOIN asset ON asset.id=jobneed.asset_id
            INNER JOIN questionset ON questionset.id=jobneed.qset_id
            INNER JOIN people on jobneed.people_id=people.id
            inner join pgroup on pgroup.id=jobneed.pgroup_id
                CROSS JOIN timezone_setting tz
                WHERE jobneed.identifier='INTERNALTOUR'
            AND jobneed.id <> 1 and jobneed.parent_id = 1
            AND bu.id <> 1
            AND jobneed.bu_id IN (SELECT unnest(string_to_array(%s, ',')::integer[]))
            AND (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE BETWEEN %s AND %s
            ORDER BY bu.buname, (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE desc
            ''',
        "PPMSummary":
            '''
            WITH timezone_setting AS (
                SELECT %s ::text AS timezone
            )
            SELECT
            assettype as "Asset Type",
            count(assettype) as "Total PPM Scheduled",
            sum(case when ((endtime AT TIME ZONE tz.timezone) <= (expirydatetime AT TIME ZONE tz.timezone) and jobstatus='COMPLETED') then 1 else 0 end) as "Completed On Time",
            sum(case when ((endtime AT TIME ZONE tz.timezone) > (expirydatetime AT TIME ZONE tz.timezone) and jobstatus='COMPLETED') then 1 else 0 end) as "Completed After Schedule",
            sum(case when jobstatus = 'AUTOCLOSED' then 1 else 0 end) as "PPM Missed",
            round((sum(case when ((endtime AT TIME ZONE tz.timezone) <= (expirydatetime AT TIME ZONE tz.timezone) and jobstatus='COMPLETED') then 1 else 0 end)::numeric/ NULLIF(count(jobstatus)::numeric,0)) * 100,2) as "Percentage",
            buname as "Site Name"
            FROM (SELECT jobneed.id,
                atype.taname AS assettype,
                jobneed.jobdesc,
                jobneed.plandatetime,
                jobneed.endtime,
                jobneed.expirydatetime,
                jobneed.jobstatus,
                jobneed.identifier,
                bu.buname,
                jobneed.bu_id as buid,
                jobneed.people_id as peopleid
            FROM jobneed
                JOIN people ON jobneed.people_id = people.id
                LEFT JOIN asset ON jobneed.asset_id = asset.id
                JOIN bt bu ON jobneed.bu_id = bu.id
                LEFT JOIN typeassist atype ON atype.id = asset.type_id
            WHERE jobneed.parent_id = '1'::integer  
            AND jobneed.plandatetime >= (now() - '60 days'::interval) AND jobneed.plandatetime <= now()
            AND jobneed.identifier='PPM') as jobneed
            cross join timezone_setting tz
            WHERE 1=1
            and buid IN (SELECT unnest(string_to_array(%s, ',')::integer[])) 
            AND (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE BETWEEN %s AND %s
            GROUP BY buname, assettype

            ''',
        "ListOfTickets":
            '''
            WITH timezone_setting AS (
                SELECT %s ::text AS timezone
            )

            SELECT
                t.id AS "Ticket No",
                t.cdtz AS created_on as "Created On ",
                t.mdtz AS "Modied On",
                t.status as "Status",
                t.ticketdesc as "Description",
                t.priority as "Priority",
                ta.taname AS ticketcategory as "Ticket Category",
                CASE
                    WHEN t.status IN ('RESOLVED', 'CLOSED') THEN TO_CHAR((t.mdtz - t.cdtz), 'HH24:MI:SS')
                    WHEN t.status = 'CANCELLED' THEN 'NA'
                    ELSE '00:00:00'
                END AS "TAT",
                CASE
                    WHEN t.status NOT IN ('RESOLVED', 'CLOSED', 'CANCELLED') THEN TO_CHAR((NOW() - t.cdtz), 'HH24:MI:SS')
                    WHEN t.status = 'CANCELLED' THEN 'NA'
                    ELSE '00:00:00'
                END AS tl,
                CASE
                    WHEN t.assignedtogroup_id IS NULL OR t.assignedtogroup_id = 1 THEN p1.peoplename
                    ELSE p2.groupname
                END AS assignedto as "Assigned To",
                p3.peoplename AS "Created By",
                p4.peoplename AS modified_by
            FROM
                ticket t
            LEFT JOIN
                people p1 ON t.assignedtopeople_id = p1.id
            LEFT JOIN
                pgroup p2 ON t.assignedtogroup_id = p2.id
            LEFT JOIN
                people p3 ON t.cuser_id = p3.id
            LEFT JOIN
                people p4 ON t.muser_id = p4.id
            LEFT JOIN
                typeassist ta ON t.ticketcategory_id = ta.id
            CROSS JOIN timezone_setting tz
            WHERE
            NOT (t.assignedtogroup_id IS NULL AND t.assignedtopeople_id IS NULL)
                AND t.bu_id IN (SELECT unnest(string_to_array(%s, ',')::integer[])) 
                
                AND NOT (t.assignedtogroup_id = 1 AND t.assignedtopeople_id = 1)
                AND NOT ((t.cuser_id = 1 or t.cuser_id IS NULL)  AND (t.muser_id = 1 or t.muser_id IS NULL))
                AND (t.cdtz AT TIME ZONE tz.timezone)::DATE BETWEEN %s AND %s
            ''',
        "WorkOrderList":
            '''
            WITH timezone_setting AS (
                SELECT %s ::text AS timezone
            )

            SELECT wom.id as wo_id, wom.cdtz as "Created On", wom.description as "Description", wom.plandatetime as "Planned Date Time", wom.endtime as "Completed On",
            array_to_string(wom.categories, ',') as "Categories", p.peoplename as "Created By", wom.workstatus as "Status", v.name as "Vendor Name", INITCAP(priority) as "Priority", bu.buname as "Site"
            from wom
            inner join people p on p.id = wom.cuser_id
            inner join vendor v  on v.id  = wom.vendor_id
            inner join bt bu on bu.id = wom.bu_id
            CROSS JOIN timezone_setting tz
            where NOT(wom.vendor_id is NULL) AND vendor_id <> 1
            AND wom.bu_id <> 1 AND wom.qset_id <> 1
            AND wom.bu_id IN (SELECT unnest(string_to_array(%s, ',')::integer[]))
            AND (wom.cdtz AT TIME ZONE tz.timezone)::DATE BETWEEN %s AND %s
            GROUP BY wom.id, bu.id, bu.buname, p.peoplename, v.name, (wom.plandatetime AT TIME ZONE tz.timezone)::DATE
            ORDER BY bu.buname, (wom.plandatetime AT TIME ZONE tz.timezone)::DATE desc
            ''',
        'SiteReport':
            '''
            WITH timezone_setting AS (
                SELECT %s::text AS timezone
            ),
            jnd_p AS (
                SELECT 
                    id AS ct_id,
                    jobdesc AS ct_jobdesc,
                    qset_id AS ct_qset_id,
                    bu_id AS ct_bu_id,
                    asset_id AS ct_asset_id,
                    starttime AT TIME ZONE tz.timezone AS ct_starttime,
                    endtime AT TIME ZONE tz.timezone AS ct_endtime,
                    performedby_id AS ct_performedby_id,
                    plandatetime AT TIME ZONE tz.timezone AS ct_plandatetime
                FROM 
                    jobneed
                CROSS JOIN 
                    timezone_setting AS tz
                WHERE 
                    parent_id IS NOT NULL 
                    AND parent_id = 1
                    AND client_id = %s
                    AND sgroup_id IN (SELECT unnest(string_to_array(%s, ',')::integer[]))
                    AND (jobneed.plandatetime AT TIME ZONE tz.timezone)::DATE BETWEEN %s AND %s
            )

            SELECT 
                jnd.jobdesc AS jobdesc,
                bt.solid as"SOL ID", 
                bt.bucode as "SITE CODE", 
                bt.buname as "SITE NAME",
                Max(qset.qsetname) AS qsetname,
                Max(asset.assetname) AS assetname,
                Max(butype.taname) AS butype,
                jnd.starttime AT TIME ZONE tz.timezone AS starttime,
                jnd.endtime AT TIME ZONE tz.timezone AS endtime,
                jnd_p.ct_plandatetime AS "DATE OF VISIT",
                Max(to_char(jnd_p.ct_plandatetime,'HH24:MI:SS')) AS "TIME OF VISIT",
                Max(ST_X(ST_PointFromText(ST_AsText(jnd.gpslocation), 4326))) AS "LONGITUDE",
                Max(ST_Y(ST_PointFromText(ST_AsText(jnd.gpslocation), 4326))) AS "LATITUDE",
                people.peoplecode AS "RP ID",
                people.peoplename AS "RP OFFICER",
                people.mobno AS "CONTACT",
                Max(bt.bupreferences->>'address') AS "SITE ADDRESS",
                Max(bt.bupreferences->'address2'->>'state') AS "STATE",
                -- Add your CASE statements here for each condition 
                -- Example:
                Max(CASE WHEN upper(question.quesname)='FASCIA WORKING' THEN jnds.answer END) AS "FACIA WORKING",
            Max(CASE WHEN upper(question.quesname)='LOLLY POP WORKING' THEN jnds.answer END) AS "LOLLY POP WORKING",
            Max(CASE WHEN upper(question.quesname)='ATM MACHINE COUNT' THEN jnds.answer END) AS "ATM MACHINE COUNT",
            Max(CASE WHEN upper(question.quesname)='AC IN ATM COOLING' THEN jnds.answer END) AS "AC IN ATM COOLING",
            Max(CASE WHEN upper(question.quesname)='ATM BACK ROOM LOCKED' THEN jnds.answer END) AS "ATM BACK ROOM LOCKED",
            Max(CASE WHEN upper(question.quesname)='UPS ROOM BEHIND ATM LOBBY ALL SAFE' THEN jnds.answer END) AS "UPS ROOM BEHIND ATM LOBBY ALL SAFE",
            Max(CASE WHEN upper(question.quesname)='BRANCH SHUTTER DAMAGED' THEN jnds.answer END) AS "BRANCH SHUTTER DAMAGED",
            Max(CASE WHEN upper(question.quesname)='BRANCH PERIPHERY ROUND TAKEN' THEN jnds.answer END) AS "BRANCH PHERIPHERI ROUND TAKEN",
            Max(CASE WHEN upper(question.quesname)='AC ODU AND COPPER PIPE INTACT' THEN jnds.answer END) AS "AC ODU AND COPPER PIPE INTACT",
            Max(CASE WHEN upper(question.quesname)='ANY WATER LOGGING OR FIRE IN VICINITY' THEN jnds.answer END) AS "ANY WATTER LOGGING OR FIRE IN VICINITY",
            Max(CASE WHEN upper(question.quesname)='FE AVAILABLE IN ATM LOBBY' THEN jnds.answer END) AS "FE AVAILABLE IN ATM LOBBY",
            Max(CASE WHEN upper(question.quesname)='DG DOOR LOCKED' THEN jnds.answer END) AS "DG DOOR LOCKED",
            Max(CASE WHEN upper(question.quesname)='DAMAGE TO ATM LOBBY' THEN jnds.answer END) AS "DAMAGE TO ATM LOBBY",
            Max(CASE WHEN upper(question.quesname)='ANY OTHER OBSERVATION' THEN jnds.answer END) AS "ATM OTHER OBSERVATION",
            Max(pgroup.groupname) as "ROUTE NAME"

            FROM 
                jnd_p
            INNER JOIN 
                jobneed AS jnd ON jnd_p.ct_id=jnd.parent_id
            INNER JOIN 
                jobneeddetails jnds ON jnd.id=jnds.jobneed_id
            INNER JOIN 
                question ON question.id=jnds.question_id
            INNER JOIN 
                bt ON bt.id=jnd.bu_id
            INNER JOIN 
                asset ON asset.id=jnd.asset_id
            INNER JOIN 
                questionset AS qset ON qset.id=jnd.qset_id
            INNER JOIN 
                people ON people.id=jnd.performedby_id
            LEFT JOIN 
                pgroup ON pgroup.id=jnd.sgroup_id
            INNER JOIN 
                typeassist AS butype ON butype.id=bt.butype_id
            CROSS JOIN 
                timezone_setting tz
            WHERE 
                upper(qset.qsetname)='SITE REPORT'
                AND jnds.answer IS NOT NULL

            GROUP BY 
                jnd.jobdesc, 
                bt.solid, 
                bt.bucode, 
                bt.buname, 
                people.peoplecode, 
                people.peoplename, 
                people.mobno,
                jnd.starttime, 
                jnd.endtime, 
                jnd_p.ct_plandatetime, 
                tz.timezone;
            '''
    }.get(query)