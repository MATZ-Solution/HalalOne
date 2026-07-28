from agents.langgraph_agent.LLMs.llm import summarizer_llm
from agents.langgraph_agent.prompts.prompt import SUMMARIZE_CONVERSATION_PROMPT
from langchain.messages import HumanMessage, AIMessage, SystemMessage
from log.logger import logger
from langchain_core.messages.utils import (
    count_tokens_approximately  
)


TURNS = [
    # --- Groceries; NUT ALLERGY planted at turn 3 -------------------------
    ("hi, do you do halal chicken nuggets?",
     "Yep, got a few good ones for you."),
    ("are those in tesco",
     "The Crestwood ones usually are, yeah."),
    ("quick thing - my sister has a nut allergy so nothing with nuts ever, for anything you show me",
     "Got it. Nuts stay out of everything from here on."),
    ("thanks. halal chocolate?",
     "Here you go."),
    ("kinnerton is the nut free one right",
     "That's the one - safe for your sister."),
    ("nice, ill grab that",
     "Good choice."),
    ("halal marshmallows",
     "These should do it."),
    ("gelatin free?",
     "Yes, all of those are."),
    ("do they do a bigger bag",
     "They do - here's the larger size."),
    ("perfect",
     "Glad that worked out."),

    # --- Dead ends + frustration; DEAD ENDS planted turns 11-12 -----------
    ("any halal pepperoni",
     "Sorry - nothing came up for that one."),
    ("what about halal salami",
     "Nothing there either. Want to try a brand name?"),
    ("honestly this is the fourth app ive tried today",
     "That sounds exhausting. You shouldn't have to work this hard for it."),
    ("i just want to make a pizza without a research project attached to it",
     "Completely fair. Let me keep digging on the topping side."),
    ("whatever, ill just do margherita",
     "Honestly not a bad shout. Let me help you get the rest right."),
    ("halal mozzarella at least?",
     "This one's solid."),
    ("does that have animal rennet",
     "Microbial, so you're fine."),
    ("good",
     "Enjoy the pizza."),

    # --- Cosmetics; HMC-ONLY RULE planted at turn 21 ----------------------
    ("switching gears, halal lipstick",
     "Here are a few."),
    ("is tuesday HFA certified?",
     "It is, yes."),
    ("i dont really trust HFA, my mosque only goes by HMC",
     "Understood - I'll stick to HMC where I can."),
    ("yeah keep that for everything not just lipstick",
     "Will do. HMC only from here on, across the board."),
    ("so which of those are HMC",
     "Only the Amara one, I'm afraid."),
    ("fine ill take amara",
     "Good pick."),
    ("halal foundation, HMC",
     "Same line, as it happens."),
    ("shade range?",
     "Twelve shades in that one."),
    ("ok",
     "Anything else?"),
    ("halal nail polish, breathable",
     "There's one, though I'll be straight with you - it's not HMC."),
    ("no HMC ones?",
     "None in the database. I'd rather tell you than substitute another body."),
    ("figures",
     "I know. It's a thin category and that's frustrating."),

    # --- Household ---------------------------------------------------------
    ("halal cleaning spray, alcohol free",
     "This should suit."),
    ("is that HMC",
     "It is, yes."),
    ("halal washing up liquid",
     "Here you go."),

    # --- INVALIDATION planted at turn 35 ----------------------------------
    ("do you have ramly burgers",
     "Yep, found them."),
    ("actually the ramly ones are out of stock everywhere near me",
     "Ah, that's a pain. Want me to find something similar you can actually get hold of?"),
    ("yeah something i can actually get",
     "Try these."),
    ("im in manchester btw",
     "Noted - I'll keep that in mind for availability."),
    ("any halal butchers near me",
     "A few in the database, though coverage up there is patchy."),
    ("fine",
     "I'll do what I can."),
    ("halal sausages, chicken",
     "These ones are HMC."),

    # ===================== TURN 40 BOUNDARY ==============================

    # --- Supplements -------------------------------------------------------
    ("halal vitamins?",
     "Here you go."),
    ("are the capsules gelatin",
     "Bovine gelatin on those, yes."),
    ("any veggie capsule ones",
     "These use a plant capsule instead."),
    ("HMC?",
     "Yes, that one's covered."),
    ("halal omega 3",
     "This is the main one."),
    ("fish based right",
     "Fish oil, yes - nothing porcine in the capsule."),
    ("ok good",
     "Anything else?"),
    ("halal baby formula",
     "Here you go."),
    ("does it have fish oil",
     "Algal DHA rather than fish oil."),
    ("halal baby snacks",
     "These are popular."),

    # ===================== TURN 50 BOUNDARY ==============================

    ("nut free?",
     "Checked - yes, safe for your sister."),
    ("good",
     "Thought you'd want that confirmed."),
    ("halal toothpaste",
     "This one."),
    ("glycerin source?",
     "Plant-derived."),
    ("halal deodorant alcohol free",
     "Here you go."),
    ("halal perfume",
     "A few options for you."),
    ("alcohol free?",
     "Oil-based, so yes."),
    ("ok",
     "Anything else?"),
    ("halal gummy vitamins for kids",
     "These are the ones."),
    ("pork gelatin in those?",
     "Bovine, and HMC certified."),

    # ===================== TURN 60 BOUNDARY ==============================

    # --- Travel ------------------------------------------------------------
    ("im travelling to spain next month, do you cover hotels",
     "I do - halal-friendly stays are in there."),
    ("halal friendly hotels barcelona",
     "Here's a start."),
    ("does it have a prayer room",
     "It does, on the ground floor."),
    ("halal restaurants barcelona",
     "This one's well reviewed."),
    ("anything not middle eastern",
     "Try this."),
    ("halal food at barcelona airport",
     "Thin on the ground, sadly. Worth packing something."),
    ("what about seville",
     "A couple of stays there."),

    # --- Turn 67: the payoff. Depends on remembering turn 3. --------------
    ("halal snacks i can take on the plane",
     "Skipping the nut bars given your sister - these are nut-free."),
    ("good catch",
     "Always."),
    ("thanks for all the help",
     "Any time. Safe travels."),
]

assert len(TURNS) == 70, f"expected 70 turns, got {len(TURNS)}"
 
 
# ---------------------------------------------------------------------------
# History builders
# ---------------------------------------------------------------------------
 
def build_history(n_turns: int):
    """Return the first n_turns of the conversation as LangChain messages."""
    if not 1 <= n_turns <= len(TURNS):
        raise ValueError(f"n_turns must be 1..{len(TURNS)}")
    messages = []
    for human, ai in TURNS[:n_turns]:
        messages.append(HumanMessage(content=human))
        messages.append(AIMessage(content=ai))
    return messages
 

def summarize_conversation( conversation_history: list, old_summary:str = "") -> list:
    token_count_before_summary = count_tokens_approximately(conversation_history) + count_tokens_approximately([AIMessage(content=old_summary)]) if old_summary else count_tokens_approximately(conversation_history)

    logger.info(f"Token count before summary: {token_count_before_summary}")
    
    turns = "\n".join(
        f"{'User' if m.type == 'human' else 'Halalify'}: {m.content}"
        for m in conversation_history
    )

    if old_summary:
        history_text = f"PREVIOUS SUMMARY:\n{old_summary}\n\nNEW TURNS:\n{turns}"
    else:
        
        history_text = f"NEW TURNS:\n{turns}"

    response = summarizer_llm.invoke([
        SystemMessage(content=SUMMARIZE_CONVERSATION_PROMPT),
        HumanMessage(content=history_text),
    ])

    token_count_after_summary = count_tokens_approximately([response])
    logger.info(f"Token count after summary: {token_count_after_summary}")
    logger.info(f"Saved: {1 - token_count_after_summary/token_count_before_summary:.0%}")
    if response.content:
        summary = response.content
        return [summary]
    else:
        return []



for n in [40, 50, 60, 70]:
        history = build_history(n)
        summary = summarize_conversation(history)
        print(f"\n===== {n} turns =====")
        print(summary)