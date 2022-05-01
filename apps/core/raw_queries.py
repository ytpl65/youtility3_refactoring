query = {
    'get_web_caps_for_client': '''
                                    WITH RECURSIVE cap(id, capsname, capscode, parent_id, cfor, depth, path, xpath) AS (
                                    SELECT id, capsname, capscode, parent_id, cfor, 1::INT AS depth, capability.capscode::TEXT AS path, capability.id::text as xpath
                                    FROM capability
                                    WHERE id = 1
                                    UNION ALL
                                    SELECT ch.id, ch.capsname, ch.capscode, ch.parent_id, ch.cfor, rt.depth + 1 AS depth, (rt.path || '->' || ch.capscode::TEXT), (xpath||'>'||ch.id||rt.depth + 1)
                                    FROM capability ch INNER JOIN cap rt ON rt.id = ch.parent_id)
                                    select * from cap
                                    order by xpath
                                ''',
    'get_childrens_of_bt':      '''
                                    WITH RECURSIVE cap(id, bucode, parent_id, butree, depth, path, xpath) AS (
                                    SELECT id,  bucode, parent_id, butree, 1::INT AS depth, bt.bucode::TEXT AS path, bt.id::text as xpath
                                    FROM bt
                                    WHERE id = %s
                                    UNION ALL
                                    SELECT ch.id, ch.bucode, ch.parent_id, ch.butree,  rt.depth + 1 AS depth, (rt.path || '->' || ch.bucode::TEXT), (xpath||'>'||ch.id||rt.depth + 1)
                                    FROM bt ch INNER JOIN cap rt ON rt.id = ch.parent_id)
                                    select * from cap
                                    order by xpath
                                ''',
    'tsitereportdetails':       '''
                                    WITH RECURSIVE nodes_cte(id, parent_id, jobdesc, people_id, qset_id, plandatetime, cdtz, depth, path, top_parent, pseqno, bu_id)
                                    as ( 
                                    SELECT id, jobneed.parent_id, jobdesc, people_id, qset_id, plandatetime, jobneed.cdtz, 1::INT AS depth, qset_id::TEXT AS path,
                                    id as top_parent, slno as pseqno, jobneed.bu_id
                                    FROM jobneed  
                                    WHERE jobneed.identifier = 'SITEREPORT' AND jobneed.parent_id=-1 AND 
                                    id<>-1 AND id= '1' 
                                    UNION ALL SELECT c.id, c.parent_id, c.jobdesc, c.people_id, c.qset_id, c.plandatetime, c.cdtz, p.depth + 1 
                                    AS depth, (p.path || '->' || c.id::TEXT) as path, c.parent_id as top_parent, slno as pseqno, c.bu_id FROM nodes_cte AS p, jobneed AS
                                    c  WHERE c.identifier='SITEREPORT' AND c.parent_id = p.id )
                                    SELECT DISTINCT jobneed.jobdesc, jobneed.pseqno, jnd.slno as cseqno, jnd.question_id, jnd.answertype, jnd.min, jnd.max, jnd.options,
                                    jnd.answer, jnd.alerton, jnd.ismandatory, q.quesname, q.answertype FROM nodes_cte as jobneed 
                                    LEFT JOIN jobneed_details as jnd ON jnd.jobneed_id=jobneed.id 
                                    LEFT JOIN question q ON jnd.question_id=q.id where jnd.answertype='Question Type' AND jobneed.parent_id <> -1 
                                    ORDER BY pseqno asc, jobdesc asc, pseqno, cseqno asc
                                ''',
    'sitereportlist':           '''
                                    SELECT * FROM( 
                                    SELECT DISTINCT jobneed.id, jobneed.plandatetime, jobneed.jobdesc, people.peoplename, 
                                    CASE WHEN (jobneed.othersite!='' or upper(jobneed.othersite)!='NONE') THEN 'other location [ ' ||jobneed.othersite||' ]' ELSE bt.buname END AS buname,
                                    jobneed.qset_id, jobneed.jobstatus AS jobstatusname, jobneed.gpslocation, bt.gpslocation AS bugpslocation, bt.pdist, count(attachment.owner) AS att,
                                    ROUND(
                                    CASE WHEN jobneed.gpslocation <> '0.0,0.0' AND bt.gpslocation <> '0.0,0.0' THEN ( 
                                    6371 * acos( cos( radians( CAST(split_part(bt.gpslocation,',',1) AS FLOAT)) ) * cos( radians( CAST(split_part(jobneed.gpslocation,',',1) AS FLOAT) ) ) * cos( radians( CAST(split_part(jobneed.gpslocation,',',2) AS FLOAT) ) - radians( CAST(split_part(bt.gpslocation,',',2) AS FLOAT)) ) + sin( radians( CAST(split_part(bt.gpslocation,',',1) AS FLOAT)) ) * sin( radians( CAST(split_part(jobneed.gpslocation,',',1) AS FLOAT) ) ) ) 
                                    ) ELSE 0 END ::numeric, 2) AS distance, 
                                    jobneed.bu_id, jobneed.remarks 
                                    FROM jobneed 
                                    INNER JOIN people ON jobneed.people_id=people.id 
                                    INNER JOIN bt ON jobneed.bu_id=bt.id 
                                    LEFT JOIN attachment ON jobneed.id=attachment.owner
                                    WHERE jobneed.parent_id=-1 AND 1=1 AND bt.id IN (%s) 
                                    AND (jobneed.qset_id IN (%s) OR jobneed.qset_id = -1) 
                                    AND jobneed.parent_id='-1' AND jobneed.plandatetime >= %s AND jobneed.plandatetime <= %s 
                                    GROUP BY jobneed.id, buname, bugpslocation, bt.pdist, people.peoplename, jobstatusname, jobneed.plandatetime)
                                    jobneed 

                                    WHERE 1=1 ORDER BY plandatetime desc OFFSET 0 LIMIT 250
                                '''
}
