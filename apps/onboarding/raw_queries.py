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
                                    order by xpath''',
    'get_childrens_of_bt':'''
                            WITH RECURSIVE cap(id, bucode, parent_id, butree, depth, path, xpath) AS (
                            SELECT id,  bucode, parent_id, butree, 1::INT AS depth, bt.bucode::TEXT AS path, bt.id::text as xpath
                            FROM bt
                            WHERE id = %s
                            UNION ALL
                            SELECT ch.id, ch.bucode, ch.parent_id, ch.butree,  rt.depth + 1 AS depth, (rt.path || '->' || ch.bucode::TEXT), (xpath||'>'||ch.id||rt.depth + 1)
                            FROM bt ch INNER JOIN cap rt ON rt.id = ch.parent_id)
                            select * from cap
                            order by xpath''',
    'tsitereportdetails': '''
                            WITH RECURSIVE nodes_cte(id, parent_id, jobdesc, peopleid_id, qsetid_id, plandatetime, cdtz, depth, path, top_parent, pseqno, buid_id)
                            as ( 
                            SELECT id, jobneed.parent_id, jobdesc, peopleid_id, qsetid_id, plandatetime, jobneed.cdtz, 1::INT AS depth, qsetid_id::TEXT AS path,
                            id as top_parent, slno as pseqno, jobneed.buid_id
                            FROM jobneed  
                            WHERE jobneed.identifier = 'SITEREPORT' AND jobneed.parent_id=-1 AND 
                            id<>-1 AND id= '1' 
                            UNION ALL SELECT c.id, c.parent_id, c.jobdesc, c.peopleid_id, c.qsetid_id, c.plandatetime, c.cdtz, p.depth + 1 
                            AS depth, (p.path || '->' || c.id::TEXT) as path, c.parent_id as top_parent, slno as pseqno, c.buid_id FROM nodes_cte AS p, jobneed AS
                            c  WHERE c.identifier='SITEREPORT' AND c.parent_id = p.id )
                            SELECT DISTINCT jobneed.jobdesc, jobneed.pseqno, jnd.slno as cseqno, jnd.quesid_id, jnd.answertype, jnd.min, jnd.max, jnd.options,
                            jnd.answer, jnd.alerton, jnd.is_mandatory, q.ques_name, q.answertype FROM nodes_cte as jobneed 
                            LEFT JOIN jobneed_details as jnd ON jnd.jobneedid_id=jobneed.id 
                            LEFT JOIN question q ON jnd.quesid_id=q.id where jnd.answertype='Question Type' AND jobneed.parent_id <> -1 
                            ORDER BY pseqno asc, jobdesc asc, pseqno, cseqno asc
                            '''
}
