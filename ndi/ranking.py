from .models import RankRequest, RankResponse, RankedPost

WEIGHTS = {'interest': .35, 'relationship': .25, 'quality': .20, 'freshness': .10, 'diversity': .10}

def rank(request: RankRequest) -> RankResponse:
    eligible = [p for p in request.posts if p.visible and (request.mode != 'following' or p.followed)]
    scored = []
    for post in eligible:
        freshness = max(0.0, 1.0 - max(0.0, request.now - post.created_at) / (7 * 86400))
        if request.mode in ('chronological', 'following'):
            score = post.created_at
        elif request.mode == 'discovery':
            score = 100 * (.45 * post.diversity + .30 * post.quality + .25 * freshness)
        else:
            score = 100 * sum(WEIGHTS[k] * v for k, v in {
                'interest': post.interest,
                'relationship': post.relationship,
                'quality': post.quality,
                'freshness': freshness,
                'diversity': post.diversity
            }.items())
        scored.append((post.id, score))
    scored.sort(key=lambda item: (-item[1], item[0]))
    return RankResponse(algorithm='NDI-A01', version='0.1.0', results=[RankedPost(id=i, score=round(s, 4)) for i, s in scored])
