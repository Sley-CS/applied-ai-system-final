# Model Card: Game Glitch Investigator

## Limitations and Biases in the System

The Game Glitch Investigator is good at catching obvious mistakes, but it still has some blind spots. The confidence score is only a simple math-based check, not proof that the system is truly smart. The game also does not adapt to how well someone is playing, so it can only give fixed feedback. Since I have to review local logs by hand, some issues could still slip through if I miss them.

## Misuse of the Game

The main risk is that someone could take the confidence score too seriously and treat it like expert advice for things like hiring or health decisions. To prevent that, the game needs clear warnings that it is only a game and should not be used for real decisions. The logic should stay server-side, logs should be protected from editing, and guess rates should be limited so the app stays stable.

## What Surprised Me About Reliability

What surprised me most was how confidently the system can still be wrong. It can show a high confidence score even when the logic is not actually trustworthy. That reminded me that reliability is not just about passing tests. It is also about making sure the system really makes sense in context.

## AI Collaboration

Working with AI felt like having a fast brainstorming partner, but one that still needed careful direction. It was helpful when it suggested a simple rate limiter to keep the game from crashing under rapid guesses. It was less helpful when it tried to replace the simple game logic with heavier machine learning ideas, which would have made the project harder to understand. I learned to treat AI suggestions as starting points and to use my own judgment before accepting them.