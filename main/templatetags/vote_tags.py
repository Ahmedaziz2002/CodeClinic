from django import template

register = template.Library()

@register.filter
def vote_count(votes, vote_type):
    return votes.filter(type=vote_type).count()
