# Layman's Guide to Agent Trajectory Visualizations

**A simple, jargon-free explanation of all 48 visualizations**

---

## 🤔 What Are These Visualizations About?

Imagine you have three different AI assistant systems that solve problems:
- **AG2**: Solves math problems by having a conversation
- **AppWorld**: Controls apps like Spotify and Email to complete tasks
- **HyperAgent**: Fixes bugs in computer code

These visualizations show **how these AI systems think and work** - like watching their "thought process" step-by-step.

---

# Part 1: AG2 Visualizations (Math Problem Solver)

## 🎯 What AG2 Does
Think of AG2 like two students working together on a math problem:
- **Student 1 (mathproxyagent)**: Asks questions and gives instructions
- **Student 2 (assistant)**: Actually solves the problem

They have a back-and-forth conversation until they get an answer.

---

## Visualization 1: **Conversation Timeline**

### What You're Looking At:
A horizontal bar chart showing each "turn" in the conversation.

### How to Read It:
- **Each horizontal bar** = One message in the conversation
- **Bar length** = How much text was in that message (longer bar = more words)
- **Colors** = Which AI agent was speaking
  - 🔴 Red = The "question asker" (mathproxyagent)
  - 🔵 Teal/Blue = The "problem solver" (assistant)
- **Symbols**:
  - ○ (circle) = Just text/talking
  - ◆ (diamond) = This message included computer code

### What This Tells You:
- How long the conversation was (more bars = longer conversation)
- Who talked more (more red bars vs more blue bars)
- When they used code vs just words

### Real Example:
Looking at `02da9c1f-7c36-5739-b723-33a7d4f8e7e7_human_timeline.png`:
- **10 turns total** - They went back and forth 10 times
- The problem solver kept saying "I need more information!"
- The question asker kept saying "Just keep trying!"
- This is like two people talking past each other

---

## Visualization 2: **Agent Participation**

### What You're Looking At:
Two side-by-side bar charts showing who did more "work."

### How to Read It:

**Left Chart - "Number of Turns":**
- Shows how many times each agent spoke
- If one bar is much bigger = that agent dominated the conversation

**Right Chart - "Total Characters":**
- Shows the total amount of text each agent wrote
- Bigger bar = that agent wrote more (was more "chatty")

### What This Tells You:
- **Balance**: Did both agents contribute equally?
- **Effort**: Who put in more work?
- Sometimes one agent talks a lot but says little (many short turns)
- Sometimes one agent talks rarely but says a lot (few long turns)

### Real Example:
In most AG2 traces:
- Both agents have roughly equal turns (balanced conversation)
- The assistant (problem solver) usually writes more text
- This is normal - the solver needs to explain their thinking!

---

## Visualization 3: **Failure Mode Annotations**

### What You're Looking At:
A list of potential "mistakes" the AI could make, color-coded.

### How to Read It:
- **🔴 Red bars** = This mistake WAS made in this conversation
- **🟢 Green bars** = This mistake was NOT made

### Common Failure Modes (In Plain English):

1. **"Unaware of stopping conditions"**
   - The AI doesn't know when to stop
   - Like a student who keeps "solving" even after getting the answer

2. **"Ignoring good suggestions from other agent"**
   - One AI gives helpful advice, the other ignores it
   - Like ignoring your study partner's correct answer

3. **"Step repetition"**
   - Doing the same thing over and over
   - Like rereading the same paragraph without understanding it

4. **"No attempt to verify outcome"**
   - Getting an answer but not checking if it's correct
   - Like not reviewing your homework before turning it in

### What This Tells You:
Which specific problems happened in this conversation. Researchers use this to understand what goes wrong with AI systems.

### Real Example:
Looking at `02da9c1f-7c36-5739-b723-33a7d4f8e7e7_human_failures.png`:
- 🔴 **"Unaware of stopping conditions"** - YES (problem!)
- 🔴 **"Ignoring good suggestions"** - YES (problem!)
- 🟢 Most other issues - NO (good!)

Translation: The AI kept asking for the answer even when the problem solver correctly said "I can't solve this without more info." Classic communication failure!

---

# Part 2: AppWorld Visualizations (App Controller)

## 🎯 What AppWorld Does
Imagine an AI "manager" who controls other AI "workers":
- **Manager (Supervisor)**: Reads your request, figures out what needs to be done
- **Workers (Spotify Agent, Email Agent, etc.)**: Actually do the work in specific apps

Like a boss delegating tasks to employees!

---

## Visualization 1: **Agent Hierarchy Graph**

### What You're Looking At:
A network diagram with circles (nodes) connected by arrows.

### How to Read It:
- **Each circle** = One AI agent
- **Arrows** = "This agent sent a message to that agent"
- **Colors** = Different apps
  - 🔴 Red = Supervisor (the boss)
  - 🟢 Green = Spotify agent
  - 🔵 Blue = Email agent
  - etc.

### What This Tells You:
Who talks to whom. Usually you'll see:
- Supervisor in the center
- Arrows pointing from Supervisor to all the specialized workers
- This shows the "chain of command"

### Real Example:
Looking at any AppWorld hierarchy graph:
```
        Supervisor
         /      \
    Spotify    Email
```
The Supervisor delegates to specialized agents. It's organized, not chaotic!

---

## Visualization 2: **Event Timeline**

### What You're Looking At:
A long vertical list of colored bars showing everything that happened, in order.

### How to Read It:
- **Read from top to bottom** = Time flows downward
- **Each bar** = One event (message, action, etc.)
- **Colors indicate type of event**:
  - 🔴 Red = Supervisor thinking/planning
  - 🔵 Blue = Worker agent responding
  - 🟢 Green = An API call (actually doing something in an app)
  - ⚪ Gray = Agent finishing its work

### Event Types Explained:
- **"Response from Supervisor"**: The boss is making a plan
- **"Entering Spotify Agent"**: Now switching to the Spotify expert
- **"Response from Spotify Agent"**: Spotify expert is working
- **"API call"**: Actually DOING something (like playing a song)
- **"Exiting Spotify Agent"**: Done with Spotify, going back to boss

### What This Tells You:
The exact sequence of what happened, like reading a transcript of a meeting.

### Real Example:
Typical flow you'll see:
1. 🔴 Supervisor: "User wants to clean up Spotify library"
2. 🔵 Entering Spotify Agent
3. 🔵 Spotify: "I need the user's login info"
4. 🔴 Supervisor: "Here's the password"
5. 🟢 API Call: `spotify.login()`
6. 🟢 API Call: `spotify.get_library()`
7. ... and so on

It's like watching a conversation where each person does their specialized job.

---

## Visualization 3: **API Usage Analysis**

### What You're Looking At:
A bar chart showing which "actions" were performed and how often.

### What's an API?
Think of it like a button on your phone:
- `spotify.login` = The "login to Spotify" button
- `spotify.show_library` = The "view my songs" button
- `gmail.send_email` = The "send email" button

### How to Read It:
- **Each bar** = One type of action
- **Bar length** = How many times that action was used
- **Colors** = Which app it belongs to

### What This Tells You:
- Which actions were most common
- How the AI actually accomplished the task
- If the AI was efficient or wasteful (did it repeat actions unnecessarily?)

### Real Example:
Looking at `aa8502b_1_api_usage.png`:
- `supervisor.show_account_passwords` - called twice (getting login info)
- `spotify.login` - called once (logging in)
- `spotify.show_library` - called multiple times (checking songs)

Translation: The AI had to look up passwords, log in, then check the library several times to complete the task.

---

# Part 3: HyperAgent Visualizations (Code Debugger)

## 🎯 What HyperAgent Does
Imagine an AI "lead engineer" who manages a team fixing bugs in software:
- **Lead (Planner)**: Reads the bug report, makes a plan
- **Navigator**: Searches through code files to find the problem
- **Editor**: Fixes the code once the problem is found

Like a team of programmers working together!

---

## Visualization 1: **Trajectory Overview**

### What You're Looking At:
Two charts side-by-side showing overall statistics.

### Left Chart - "Event Type Distribution" (Pie Chart):
Each slice shows what percentage of time was spent on different activities:
- **Planner** slice = Planning/strategizing time
- **Navigator** slice = Searching for code
- **Tool call** slice = Actually doing something (opening files, searching)
- **System** slice = Background admin stuff

### Right Chart - "Agent Activity" (Bar Chart):
Shows how many things each team member did:
- Bigger bar = That agent was busier

### What This Tells You:
- How the team divided up the work
- If one agent did most of the heavy lifting
- What kind of activities dominated (planning vs. doing)

### Real Example:
Looking at any HyperAgent overview:
- Usually **Navigator** has the biggest slice (lots of searching)
- **Tool calls** are frequent (lots of file opening)
- This makes sense: finding bugs requires searching through lots of files!

---

## Visualization 2: **Tool Usage Distribution**

### What You're Looking At:
A bar chart showing which "tools" (actions) were used most.

### Tools Explained (Like a Programmer's Toolbox):

- **`open_file`**: Open a file to read it
  - Like double-clicking a file on your computer

- **`get_folder_structure`**: See what files are in a directory
  - Like opening a folder to see what's inside

- **`find_file`**: Search for a file by name
  - Like using the search bar on your computer

- **`keyword_search`**: Search for specific words in files
  - Like Ctrl+F (Find) in a document

- **`editor`**: Make changes to a file
  - Like editing a Word document

### How to Read It:
- **Each bar** = One tool
- **Bar height** = How many times it was used
- **Taller bar** = More important for this task

### What This Tells You:
How the AI actually went about debugging:
- Lots of `open_file` = Had to read many files to understand the code
- Lots of `keyword_search` = Had to hunt for specific pieces of code
- Few `editor` calls = Only made small, targeted fixes (good!)

### Real Example:
Looking at `pallets__flask-5063_human_tools.png`:
- `open_file`: 15 times (read lots of files)
- `keyword_search`: 10 times (searched for specific code)
- `editor`: 3 times (made just a few focused edits)

Translation: The AI spent most of its time searching and reading to understand the problem, then made precise fixes. Like a surgeon: lots of diagnosis, minimal cutting!

---

## Visualization 3: **Failure Mode Analysis**

Same as AG2's failure modes! Shows which mistakes were made:
- 🔴 Red = This problem happened
- 🟢 Green = This problem didn't happen

### Common HyperAgent Failure Modes:

1. **"No attempt to verify outcome"**
   - Fixed the code but didn't test if it works
   - Like fixing a car without test-driving it

2. **"Derailing from task objectives"**
   - Got distracted and worked on the wrong thing
   - Like going off on a tangent

3. **"Step repetition"**
   - Kept searching the same files over and over
   - Like checking the fridge multiple times hoping food appears

---

# Part 4: Unified Visualizations (Comparing All Three)

## 🎯 Purpose
These compare AG2, AppWorld, and HyperAgent side-by-side to see how they differ.

---

## Visualization 1: **comparison.png**

### What You're Looking At:
Four charts comparing the three AI systems.

### Chart 1 - "Average Trajectory Length"
- Shows how many steps each AI system typically takes
- **Finding**: HyperAgent takes WAY more steps (128 on average)
- **Why**: Debugging code is complex; math problems are simpler

### Chart 2 - "Average Tool/API Usage per Trace"
- Shows how many actions each system performs
- **Finding**: HyperAgent uses the most tools (25.6 per task)
- **Why**: Lots of file reading and searching needed

### Chart 3 - "Average Failure Modes Present"
- Shows which system makes more mistakes
- **Finding**: HyperAgent has more failures (2.2 on average)
- **Why**: Harder tasks = more chances for mistakes

### Chart 4 - "Traces Processed by Agent Type"
- Just shows we analyzed 5 traces from each system

### Key Takeaway:
**Complexity ranking**: HyperAgent >> AppWorld > AG2

More complex tasks need more steps, more tools, and have more failure opportunities.

---

## Visualization 2: **ag2_failure_patterns.png**

### What You're Looking At:
A bar chart showing which mistakes AG2 makes most often (across 20 different math problems).

### How to Read It:
- **Each bar** = One type of mistake
- **Bar length** = How many times (out of 20) this mistake happened
- **Longer bar** = More common problem

### Common Patterns You'll See:
- "Unaware of stopping conditions" is usually the longest bar
  - The AI doesn't know when to stop trying
  - Happens in ~40% of cases

- "Step repetition" is also common
  - Doing the same calculation multiple times
  - Happens in ~20-30% of cases

### What This Tells You:
The most common weaknesses of the AG2 system. If you were improving AG2, you'd focus on these issues first!

---

## Visualization 3: **hyperagent_failure_patterns.png**

Same as above, but for HyperAgent (the code debugger).

### Common Patterns You'll See:
- "No attempt to verify outcome" is usually longest
  - The AI fixes code but doesn't test it
  - Happens in ~50% of cases!

- "Derailing from task objectives"
  - Gets distracted by irrelevant code
  - Happens in ~30% of cases

### What This Tells You:
HyperAgent's biggest weakness is not verifying its work. It makes changes but doesn't check if they actually fix the bug!

---

# 📊 Quick Reference: What Each Visualization Tells You

| Visualization | What It Shows | Key Question It Answers |
|---------------|---------------|-------------------------|
| **AG2 Timeline** | Conversation flow | Who said what and when? |
| **AG2 Participation** | Work distribution | Did both agents contribute equally? |
| **AG2 Failures** | Mistakes made | What went wrong in this conversation? |
| **AppWorld Hierarchy** | Team structure | Who reports to whom? |
| **AppWorld Timeline** | Event sequence | What happened in what order? |
| **AppWorld API Usage** | Actions performed | What did the AI actually DO? |
| **HyperAgent Overview** | Work breakdown | How was time spent? |
| **HyperAgent Tools** | Tool usage | Which tools were most important? |
| **HyperAgent Failures** | Mistakes made | What went wrong while debugging? |
| **Comparison** | System differences | Which AI system is most complex? |
| **AG2 Failure Patterns** | Common mistakes | What are AG2's weaknesses? |
| **HyperAgent Failure Patterns** | Common mistakes | What are HyperAgent's weaknesses? |

---

# 🎨 Color Guide

## AG2 Colors:
- 🔴 **Red (#FF6B6B)**: mathproxyagent (the questioner)
- 🔵 **Teal (#4ECDC4)**: assistant (the solver)
- 🔴 **Dark Red (#E74C3C)**: Failure present
- 🟢 **Green (#27AE60)**: Failure absent

## AppWorld Colors:
- 🔴 **Red (#FF6B6B)**: Supervisor (the boss)
- 🟢 **Spotify Green (#1DB954)**: Spotify agent
- 🔵 **Gmail Blue (#EA4335)**: Gmail agent
- 🟠 **Orange (#FF9900)**: Amazon agent

## HyperAgent Colors:
- 🔴 **Red (#FF6B6B)**: Planner (the lead)
- 🔵 **Teal (#4ECDC4)**: Navigator (the searcher)
- 🔵 **Blue (#45B7D1)**: Editor (the fixer)
- 🟣 **Purple (#9B59B6)**: get_folder_structure tool
- 🔵 **Blue (#3498DB)**: open_file tool

---

# 🤓 Reading Tips

## For Beginners:
1. **Start with the simple ones**: AG2 Timeline is easiest to understand
2. **Look for patterns**: Longer bars = more activity
3. **Colors are your friend**: Same color = same agent/tool
4. **Don't worry about details**: Big picture matters more

## Questions to Ask Yourself:
- **Timeline**: Does the conversation look balanced or one-sided?
- **Participation**: Did one agent dominate?
- **Hierarchy**: Is the structure clear or messy?
- **Tool Usage**: Was one tool used way more than others?
- **Failures**: How many red bars (problems) vs green bars (no problems)?

## What "Good" Looks Like:
- **Balanced participation**: Both agents contribute
- **Clear hierarchy**: Organized delegation
- **Efficient tool use**: Few repeated actions
- **Few failures**: Mostly green bars, few red bars
- **Short trajectories**: Got to the answer quickly

## What "Bad" Looks Like:
- **One agent dominates**: Unbalanced conversation
- **Messy hierarchy**: Unclear who does what
- **Lots of repetition**: Same action over and over
- **Many failures**: Lots of red bars
- **Very long trajectories**: Took forever to solve

---

# ❓ FAQ

## Q: Why are some traces longer than others?
**A:** Harder problems need more steps! Just like harder homework takes longer.

## Q: Is it bad if there are failure modes?
**A:** Not necessarily! Even humans make these mistakes. Researchers study these to improve AI.

## Q: Which AI system is "best"?
**A:** Depends on the task:
- AG2: Best for math
- AppWorld: Best for app automation
- HyperAgent: Best for code debugging

## Q: Why do colors matter?
**A:** Colors help you quickly see patterns. Red agents, blue agents, green tools - your brain processes colors faster than reading labels!

## Q: What if I see a really long bar?
**A:** That agent/tool/event was very active or produced lots of text. Could be good (working hard) or bad (being inefficient).

## Q: Can I generate more visualizations?
**A:** Yes! Just run: `python3 generate_all_visualizations.py`

---

# 🎯 Real-World Analogies

| AI Concept | Real-World Analogy |
|------------|-------------------|
| **AG2 Agents** | Two students working on homework together |
| **AppWorld Supervisor** | Manager delegating tasks to employees |
| **HyperAgent Team** | Engineering team fixing a bug |
| **Trajectory** | A transcript of a meeting |
| **Tool Call** | Pressing a button or using a tool |
| **Failure Mode** | Common mistake people make |
| **API** | App feature (like a button) |
| **Timeline** | Step-by-step story of what happened |

---

# 📝 Summary

You now have **48 visualizations** that show:

1. **How AI agents communicate** (timelines, hierarchies)
2. **What actions they take** (tool usage, API calls)
3. **What mistakes they make** (failure modes)
4. **How they compare** (unified analysis)

All using **real data** from actual AI systems solving real problems!

Think of these visualizations as "X-rays" into AI systems - they let you see what's happening inside the "black box" of AI decision-making.

**No technical background needed** - just look at the colors, patterns, and bar lengths to understand what's going on! 🎨
