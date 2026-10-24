# LinkedIn post draft (NOT posted)

Formula: F17 Controlled A/B Anecdote, restyled after studying Himanshu Prajapati's top posts
(underdog opening, one chased question, numbered lessons, honest limits, invitation to correct).
Goal: comments. Post window: Tue/Wed/Thu, 7:30 to 9:00 AM IST.
Attach: results/charts/obeyed_by_technique.png

## Post body

My 8 GB Mac ran a 4B model. It followed an instruction hidden in white text on a web page. NVIDIA's 550B model ignored every trap I gave it: 12 out of 12.

I wanted to know one thing. Does an AI browser agent follow instructions the user never wrote?

So I built 20 trap pages, each hiding one instruction a different way. A small server logs what the agent does.

28 runs on trap pages. 3 obeyed.

What I found:

1. Hiding style mattered more than model size. All 3 obeyed runs came from white-on-white text or a fake system banner. HTML comments, hidden form fields and alt text got 0 of 10.

2. Size did not predict it. On the 3 pages both models saw, the 4B model obeyed 2 and the 550B model obeyed 0.

3. One model dropped the job. Cohere's north-mini-code was told to abandon the task. It answered "CANCELLED2013" and never gave the price.

4. Nobody leaked the secret I planted. The 7 clean control pages were never obeyed.

The honest part: my first big run was mostly junk. The free API quota ran out and I threw away 44 broken results. What is left is small: 35 valid runs, 14 of my 20 pages, one try per local model. I checked 20 runs by hand against my scorer and all 20 matched.

Treat it as a sketch. If my test is wrong somewhere, tell me where.

What would you check before letting an agent read a page you do not control?

#AIAgents #PromptInjection

## First comment (links go here, not in the body)

Write-up and the code to rerun it:
[dev.to link, fill in after the blog is live]
https://github.com/Saurabhsing21/Browser-use-agent
