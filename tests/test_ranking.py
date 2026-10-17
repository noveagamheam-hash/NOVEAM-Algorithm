from ndi.models import RankRequest, Post
from ndi.ranking import rank

def test_visibility_and_following():
    base = dict(created_at=100, interest=.8, relationship=.7, quality=.9, diversity=.4)
    req = RankRequest(now=200, mode='following', posts=[
        Post(id='a', author_id='u1', followed=True, **base),
        Post(id='b', author_id='u2', followed=False, **base),
        Post(id='c', author_id='u3', followed=True, visible=False, **base)
    ])
    assert [x.id for x in rank(req).results] == ['a']

def test_newest_first():
    base = dict(interest=.5, relationship=.5, quality=.5, diversity=.5)
    req = RankRequest(now=300, mode='chronological', posts=[
        Post(id='old', author_id='a', created_at=100, **base),
        Post(id='new', author_id='b', created_at=200, **base)
    ])
    assert [x.id for x in rank(req).results] == ['new', 'old']
