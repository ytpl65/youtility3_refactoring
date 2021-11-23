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
                            order by xpath'''
}
