import unittest
from pathlib import Path
from connections import Connections


def person(identity, name=None):
    return dict(id=identity, name=name or identity)


class ConnectionsTests(unittest.TestCase):
    def setUp(self):
        self.index = Connections([
            ('movies', Path('1.json'), dict(title='Film', cast_main=[person('a'), person('b')],
                 cast_other=[person('b'), person('c')], directors=[person('d'), person('a')])),
            ('series', Path('2.json'), dict(title='Serial', cast_main=[person('a'), person('b')],
                 directors=[person('d')])),
        ])

    def test_counts_roles_and_no_self_connections(self):
        graph = self.index.graph('id:a')
        counts = {(n['id'], n['role']): n['count'] for n in graph['nodes']}
        self.assertEqual(counts, {('id:b', 'actor'): 2, ('id:c', 'actor'): 1, ('id:d', 'director'): 2})
        self.assertEqual(graph['projects'], 2)
        self.assertEqual(len(graph['nodes'][0]['projects']), 2)

    def test_kind_filter_and_director_perspective(self):
        graph = self.index.graph('id:d', 'director', 'series')
        self.assertEqual({n['id'] for n in graph['nodes']}, {'id:a', 'id:b'})
        self.assertTrue(all(n['role'] == 'actor' and n['count'] == 1 for n in graph['nodes']))
        self.assertEqual(self.index.graph('id:c', kind='series')['nodes'], [])

    def test_limit_per_role_and_search(self):
        self.assertEqual(len(self.index.graph('id:a', limit=1)['nodes']), 2)
        self.assertEqual([p['id'] for p in self.index.search(' D ', 'director')], ['id:d'])
        self.assertEqual(self.index.search('c', 'director'), [])
        with self.assertRaises(KeyError):
            self.index.graph('unknown')

    def test_identity_not_name_and_missing_ids(self):
        index = Connections([('movies', Path('1'), dict(cast_main=[person('1', 'Jan'), person('2', 'Jan'), person('', 'Ewa')]))])
        self.assertEqual(len(index.people), 3)
        self.assertEqual(len(index.graph('name:ewa')['nodes']), 2)


if __name__ == '__main__':
    unittest.main()
