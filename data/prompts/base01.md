Move inbox tasks into existing projects or leave in inbox with reason.

EXACT OUTPUT FORMAT REQUIRED:
1. Start with existing projects (unchanged)
2. Then existing tasks (unchanged) 
3. Then new/modified tasks only
4. Then inbox items that couldn't be classified

RULES:
- Keep existing project/task lines exactly as shown
- For new tasks: use next available ID in sequence
- For unmatched tasks: format as "TaskName;Reason for staying in inbox"
- NO project creation allowed
- NO explanatory text
- NO markdown formatting

# Current Data:
1;Kitchen Renovation
2;Bathroom Upgrade  
3;Career Development
1;10;Install cabinet handles;60m;physical,need-tools,carpentry
1;11;Fix leaky faucet;45m;physical,need-tools,plumbing
1;12;Order new countertop;30m;digital,buy
2;20;Replace toilet;2h;physical,need-tools,plumbing
2;21;Tile shower walls;6h;physical,need-tools,need-material,tiling
3;30;Update LinkedIn;30m;digital
3;31;Practice coding interview;2h;digital

# Inbox to Process:
Install new kitchen cabinet handles
Fix leaky bathroom sink
Paint accent wall in bedroom
Replace broken light switch
Repair loose deck railing

OUTPUT EXACTLY THIS STRUCTURE:
[Keep all existing lines above unchanged]
[Add new classified tasks with incremented IDs]
[Add unmatched tasks in format: TaskName;Reason]
