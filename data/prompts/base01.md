Move inbox task into existing projects. 
Constraints:
* If not enough confidence then leave them in Inbox  with reason as description (title;reason)
* Respond in exact CVS format in code qutoes ```
* increment id for new task
* add tags from available if suitable

```
# Projects (pid=0)
1;Kitchen Renovation
2;Bathroom Upgrade
3;Career Development

# Tasks under Kitchen Renovation (pid=1)
1;10;Install cabinet handles;60m;physical,need-tools,carpentry
1;11;Fix leaky faucet;45m;physical,need-tools,plumbing
1;12;Order new countertop;30m;digital,buy

# Tasks under Bathroom Upgrade (pid=2)
2;20;Replace toilet;2h;physical,need-tools,plumbing
2;21;Tile shower walls;6h;physical,need-tools,need-material,tiling

# Tasks under Career Development (pid=3)
3;30;Update LinkedIn;30m;digital
3;31;Practice coding interview;2h;digital

# Inbox items 
Install new kitchen cabinet handles
Fix leaky bathroom sink
Paint accent wall in bedroom
Replace broken light switch
Repair loose deck railing
```