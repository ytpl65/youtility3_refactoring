query = {
    'get_web_caps_for_client' : '''
                                    WITH RECURSIVE cap(capsid, capsname, capscode, parent, cfor, depth, path) AS (
                                    SELECT capsid, capsname, capscode, parent, cfor, 1::INT AS depth, capability.capsid::TEXT AS path
                                    FROM capability
                                    WHERE capsid = 1
                                    UNION ALL
                                    SELECT ch.capsid, ch.capsname, ch.capscode, ch.parent, ch.cfor, rt.depth + 1 AS depth, (rt.path || '->' || ch.capsid::TEXT) 
                                    FROM capability ch INNER JOIN cap rt ON rt.capsid = ch.parent)
                                    select * from cap
                                    order by path'''
}