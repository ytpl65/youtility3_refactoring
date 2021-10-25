query = {
    'get_web_caps_for_client': '''
                                    WITH RECURSIVE cap(id, capsname, capscode, parent, cfor, depth, path) AS (
                                    SELECT id, capsname, capscode, parent, cfor, 1::INT AS depth, capability.id::TEXT AS path
                                    FROM capability
                                    WHERE id = 1
                                    UNION ALL
                                    SELECT ch.id, ch.capsname, ch.capscode, ch.parent, ch.cfor, rt.depth + 1 AS depth, (rt.path || '->' || ch.id::TEXT) 
                                    FROM capability ch INNER JOIN cap rt ON rt.id = ch.parent)
                                    select * from cap
                                    order by path'''
}
