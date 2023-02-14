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
                                    id as top_parent, seqno as pseqno, jobneed.bu_id
                                    FROM jobneed  
                                    WHERE jobneed.identifier = 'SITEREPORT' AND jobneed.parent_id=-1 AND 
                                    id<>-1 AND id= '1' 
                                    UNION ALL SELECT c.id, c.parent_id, c.jobdesc, c.people_id, c.qset_id, c.plandatetime, c.cdtz, p.depth + 1 
                                    AS depth, (p.path || '->' || c.id::TEXT) as path, c.parent_id as top_parent, seqno as pseqno, c.bu_id FROM nodes_cte AS p, jobneed AS
                                    c  WHERE c.identifier='SITEREPORT' AND c.parent_id = p.id )
                                    SELECT DISTINCT jobneed.jobdesc, jobneed.pseqno, jnd.seqno as cseqno, jnd.question_id, jnd.answertype, jnd.min, jnd.max, jnd.options,
                                    jnd.answer, jnd.alerton, jnd.ismandatory, q.quesname, q.answertype FROM nodes_cte as jobneed 
                                    LEFT JOIN jobneed_details as jnd ON jnd.jobneed_id = jobneed.id 
                                    LEFT JOIN question q ON jnd.question_id = q.id where jnd.answertype='Question Type' AND jobneed.parent_id <> -1 
                                    ORDER BY pseqno asc, jobdesc asc, pseqno, cseqno asc
                                ''',
    'sitereportlist':           '''
                                    SELECT * FROM(
                                    SELECT DISTINCT jobneed.id, jobneed.plandatetime, jobneed.jobdesc, people.peoplename, 
                                    CASE WHEN (jobneed.othersite!='' or upper(jobneed.othersite)!='NONE') THEN 'other location [ ' ||jobneed.othersite||' ]' ELSE bt.buname END AS buname,
                                    jobneed.qset_id, jobneed.jobstatus AS jobstatusname, ST_AsText(jobneed.gpslocation) as gpslocation, bt.pdist, count(attachment.owner) AS att,
                                    jobneed.bu_id, jobneed.remarks 
                                    FROM jobneed 
                                    INNER JOIN people ON jobneed.people_id = people.id 
                                    INNER JOIN bt ON jobneed.bu_id = bt.id 
                                    LEFT JOIN attachment ON jobneed.uuid::text = attachment.owner
                                    WHERE jobneed.parent_id=1 AND 1 = 1 AND bt.id IN %s 
                                    AND jobneed.identifier='SITEREPORT'
                                    AND jobneed.plandatetime >= %s AND jobneed.plandatetime <= %s 
                                    GROUP BY jobneed.id, buname,  bt.pdist, people.peoplename, jobstatusname, jobneed.plandatetime)
                                    jobneed 
                                    WHERE 1 = 1 ORDER BY plandatetime desc OFFSET 0 LIMIT 250
                                ''',

    'incidentreportlist':        '''
                                    SELECT * FROM(
                                    SELECT DISTINCT jobneed.id, jobneed.plandatetime, jobneed.jobdesc,  jobneed.bu_id, 
                                    case when (jobneed.othersite!='' or upper(jobneed.othersite)!='NONE') then 'other location [ ' ||jobneed.othersite||' ]' else bt.buname end  As buname,
                                    people.peoplename, jobneed.jobstatus as jobstatusname, count(attachment.owner) as att, ST_AsText(jobneed.gpslocation) as gpslocation
                                    FROM jobneed 
                                    INNER JOIN people ON jobneed.people_id=people.id 
                                    INNER JOIN bt ON jobneed.bu_id=bt.id 
                                    LEFT JOIN attachment ON jobneed.uuid::text = attachment.owner 
                                    WHERE jobneed.parent_id=1 AND jobneed.identifier = 'INCIDENTREPORT' 
                                    AND bt.id IN %s 
                                    AND jobneed.plandatetime >= %s AND jobneed.plandatetime <= %s
                                    AND attachment.attachmenttype = 'ATTACHMENT'
                                    GROUP BY jobneed.id, buname, people.peoplename, jobstatusname, jobneed.plandatetime)
                                    jobneed
                                    where 1=1 ORDER BY plandatetime desc OFFSET 0 LIMIT 250
                                ''',
    'workpermitlist':           '''
                                SELECT * FROM( 
                                SELECT DISTINCT workpermit.id, workpermit.cdtz,workpermit.seqno, qset.qsetname as wptype, workpermit.wpstatus, workpermit.workstatus,
                                workpermit.bu_id,  bt.buname  As buname,
                                pb.peoplename, p.peoplename as user, count(attachment.uuid) as att

                                FROM workpermit INNER JOIN people ON workpermit.muser_id=people.id
                                INNER JOIN people p ON workpermit.cuser_id=p.id
                                INNER JOIN people pb ON workpermit.approvedby_id=pb.id
                                INNER JOIN bt ON workpermit.bu_id=bt.id
                                INNER JOIN questionset qset ON workpermit.wptype_id=qset.id
                                LEFT JOIN attachment ON workpermit.uuid=attachment.owner 

                                WHERE workpermit.parent_id=1 
                                AND 1=1 AND attachment.attachmenttype = 'ATTACHMENT'
                                AND workpermit.bu_id IN (%s) 
                                AND workpermit.parent_id='1' 
                                AND workpermit.id != '1' 
                                AND workpermit.cdtz >= now() - interval '100 day' 
                                AND workpermit.cdtz <= now()
                                GROUP BY workpermit.id, buname, people.peoplename, qset.qsetname, workpermit.wpstatus, workpermit.workstatus,pb.peoplename, p.peoplename)workpermit 
                                WHERE 1=1 ORDER BY cdtz desc''',
'get_ticketlist_for_escalation':'''SELECT DISTINCT ticket.cdtz + INTERVAL '1 minute' * escalation.calcminute as exp_time, escalation.level,       
                 escalation.frequency AS efrequency, escalation.frequencyvalue, escalation.calcminute,                 
                 escalation.assignedperson_id, escalation.assignedgroup_id, escalation.body, ticket.ticketdesc,           
                ticket.comments,  ticket.performedby_id, ticket.priority,                  
                 ticket.cuser_id, ticket.muser_id,  
                 ticket.cdtz, ticket.mdtz,  ticket.id as ticketno, ticket.bu_id,                                
                ticket.level, ticket.ticketcategory_id                                             
                 FROM(                                                                                                 
                    SELECT A.*                                                                                         
                    FROM ticket A                                                                                     
                    WHERE A.status NOT IN ('CANCELLED', 'COMPLETED', 'ESCALATED', 'RESOLVED') and 
                    A.isescalated=false                      
                 )ticket,                                                                                              
                 (                                                                                                     
                    SELECT id,escalationtemplate_id,  level, frequency, frequencyvalue,                                           
                    CASE WHEN frequency = 'MINUTE' THEN frequencyvalue                                                 
                         WHEN frequency = 'HOUR'   THEN frequencyvalue * 60                                            
    	                 WHEN frequency = 'DAY'    THEN frequencyvalue * 24 * 60                                       
	                     WHEN frequency = 'WEEK'   THEN frequencyvalue * 07 * 24 * 60                                  
                    END calcminute,                                                                                    
                    assignedperson_id, assignedgroup_id, body, cuser_id, cdtz, muser_id, mdtz, bu_id                                            
                    FROM escalationmatrix WHERE escalationtemplate_id <> 1                       
                 )escalation                                                                                           
                 WHERE (ticket.level+1)=escalation.level                                                               
                    AND escalation.bu_id=ticket.bu_id                                                                    
                    AND ticket.ticketcategory_id=escalation.escalationtemplate_id                                                      
                    AND ticket.cdtz + INTERVAL '1 minute' * escalation.calcminute < now();  '''
}
