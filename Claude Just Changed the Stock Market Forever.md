(Transcribed by TurboScribe. Go Unlimited to remove this message.)

Claude just changed how we trade stocks forever and it's because of this new skill that lets it access live market data, track what Wall Street, whales and US politicians are buying and use that to play the stock market with all that information automatically. I've actually been using this for the past couple of weeks and it's completely changed how I think about trading. So in this video I'm going to be breaking down how you can get started in three levels. 

So first we're going to get set up. I'll walk you through the basics of how trading works and we'll get Claude and all the we're going to be building a copy trading bot. I'm going to be showing you how to track what Wall Street whales and US politicians are buying and have Claude copy their exact moves automatically.

And level three, we're going to get into options. I'll break down what they are, how they work, and then we're going to be building a bot that runs one of the most consistent income strategies in trading called the wheel strategy. And even if you've never bought a single stock before or have zero technical background, you'll be able to do this because all we're going to be doing is simply speaking to Claude. 

Let's get into it. Okay, before we get into anything, I need to give you some context on why I'm actually making this video and why this matters. Because for the first few years of my career, I used to work at JP Morgan and I actually got to see how institutional trading works up close. 

And the biggest thing I took away from that is the gap between Wall Street and regular people comes down to just three things. First, it's the data. So imagine like a poker game and you're sitting at a table with your two cards trying to figure out what to do. 

But the person across from you can see every card on the table and every card in your hand. You'd probably never sit down at that table, right? And that's the stock market. That's what you're playing against every single day. 

Wall Street knows when a billionaire places a massive bet on a stock. They know when a senator buys shares right before a major announcement. They see where the money is moving before you even hear about it on the news. 

And by the time you do hear about it, they've already made their money. So you're stuck trading against people who have the information you don't have any access to. And unfortunately, that's the game. 

That's the kind of access that used to cost hundreds of thousands of dollars a year. But now I'll show you how to access that kind of information with a single click of a few buttons. Second is execution.

Say you spot the perfect trade, but you're at lunch or you hesitate for like 10 minutes and the window closes. Wall Street doesn't deal with that. They have systems watching the market and placing trades around the clock automatically. 

And luckily, Claude can do that too. Which brings us to number three, which is intelligence. Having the data and the speed really means nothing if you don't have a plan. 

The big guys have teams reading all that information and making calculated decisions. And to do all of that, you need to buy expensive tools. And if you couldn't afford the tools, you were locked out. 

But with Claude and these new skills, that barrier is gone. And I'm going to show you how to set all of that up. All right, let's build this thing. 

I'm going to be explaining everything as we go. So if you're brand new, just follow along. So if our goal is to get Claude to trade stocks for us, to do that, Claude needs two things. 

It needs somewhere to place the trades and it needs the information to decide what to trade. Let's start with the first one. And actually back in the day, if you wanted to buy a stock, you'd have to call a person on the phone and say something like, I don't know, buy me 50 shares of IBM. 

That person was go to the stock exchange and make that happen for you. That whole system, the firm, the person, the access to the exchange, that's called a brokerage. But today it's an app. 

You open up Robinhood or Fidelity or tap a button and you own a stock. That's the same concept with just no phone call. But here's where it gets interesting for us. 

Some brokerages actually let you skip that step entirely and connect it through code. And because Claude is so good at coding, that's what we need because we're not going to be the ones trading. Claude is. 

And we're going to be using a tool today called Alpaca. It's free to sign up and it gives you API access, which is how we're going to get Claude to connect to it and place trades on our behalf. So let me show you how to do that. 

But more importantly, before we get any further, quick disclaimer, I'm not a financial advisor. This is not financial advice. I'm just showing you how to build cool stuff with AI. 

And everything we're doing today is in paper trading. And paper trading means that you're using fake money in a real market. So it's the same stocks, the same prices, everything behaves the same way. 

You're just not risking a single dollar. OK, so let's connect Claude to our brokerage. OK, so to get started, what we're need first is the Claude desktop app. 

All right. So I'm going to do Claude.com slash download. And if you need any of these links, it's going to be in the link in the description below.

If I'm going here and you see you just want to download this app and you can use it for Windows or Mac. But make sure you download the Claude desktop app. OK. 

All right. So after you install the app, you'll get something that looks like this. Make sure your software or your Mac OS is up to date so you have everything available. 

And ideally you have the pro or the max version of Claude paid for. OK, so that's step number one. Step number two is we need to make our brokerage account. 

So I'm going to go back into my browser and I'm going to search up Alpaca. And you can see Alpaca trading platform. And I'm going to go here and I'm going to sign up.

All right. So after you enter all your information and you go through, you're going to see you have this dashboard right here. And in this dashboard, if I go to the top left and I open this up and you see I have an individual trading account, but everything we're going to be doing is not with real money. 

It's with paper money. So what we're going to be using is this paper trading account. OK. 

And you can, you know, if you want to make a new one, I'm going to say I'm trading Claude. And let's say we can give ourselves, I don't know, fifty thousand dollars. OK. 

And save. And you can see right there we're going to have a trading Claude account and I'm going to click this. So now I have fifty thousand dollars to essentially play with in the stock market. 

All right. Now I'm going to show you how to get this connected with Claude to get this connected with Claude. What we're going to do is I'm going to scroll down right here and you see right here where it says API keys. 

What we want to do is hit generate new API keys. OK. And you can see there's three things. 

Endpoint, key and secret. We're going to need all three of these. All right. 

So let's get Claude set up. I'm going to go back to my Claude app. And here, what I want you to do right now is hit this thing that says code. 

OK. It's the same thing. We're just going to be talking to it. 

But all it is, is a little bit of a different interface. OK. So cool. 

We see this little guy here and that means we're good to go. And I'm going to do is right here. I want you to hit this button right here and hit a new folder.

OK. Because we want to keep everything we're doing organized. I'm going to go to documents and I'm going to hit new folder and I'm going to call it trading. 

OK. So now everything we do is going to be saved into this trading folder. All right. 

OK. I'm going to move this to the side. Now, what I'm going to do is I'm going to be pasting in right here this and then go back to Claude and then say endpoint. 

I'm going to say key. Oops. Claude key. 

And then I'm going to say copy this one and then go to Claude and then say secret. OK. Now. 

Let's see if we can get our Claude to trade a simple stock just to make sure our connection is solid. And after a connection is solid, we'll build layers on top of that so we can actually get it to do some really cool stuff. Right. 

All right. So what I'm going to be telling it is this. Hey, what I want you to do. 

I just gave you the documentation and my keys to connect to my Alpaca trading account. I'm just testing the connection right now. Can you please buy one share of Apple? I want to see it inside my account.

All right. Great. So all this is good right now just to make it a little faster. 

I'm going to right here click on it because this is a very easy command and I'm going to hit go. All right. So it's saying the order is placed successfully. 

Here's the summary. Now, if I go back here, if I reload. OK. 

Awesome. Right. So you see, I already bought a share of Apple. 

Now you can trade by just talking to it and be like, hey, can you sell that share of Apple and then buy a share of Tesla? Great. Trust Workspace. And here, this is what I want you to do as well. 

Hey, can you make sure in this folder you save these credentials so I don't have to keep giving it to you when we want to trade? We're going to be using this account and in this folder, we're going to be doing a lot of trades. OK, so what we're going to do is because right here we gave it access to all this stuff, I want to make sure I don't have to keep giving it access. I'm just getting it to save these credentials inside a file.

Right now, Claude can trade, but it's trading blind. It doesn't know what to buy, when to buy or why. It's missing the most important piece, which is strategy. 

So let's get into that. In this level, we're going to turn Claude into something that runs on its own. So basically a bot that watches the market, makes its own decisions and based on the rules you set. 

And the first strategy we're going to make, you can think of it like a smart thermostat. Once you set the rules, if the room temperature, let's say, drops below 68 degrees Fahrenheit, you're going to turn on the heat. If it goes above 75 degrees Fahrenheit, you kick on the AC. 

That means you don't have to sit there fiddling with your phones, messing with the temperature all day. The thermostat does that for you. It checks, it acts and adjusts. 

And the bot is going to work exactly the same way. That means we're going to be setting some rules. And let me show you how this works by actually explaining the trailing stop strategy, which is a really good strategy used by many different traders. 

Let me show you how the trailing stop strategy actually works. So say you buy a stock at a hundred dollars. Well, let's say we tell Claude, if this drops to $95, sell it. 

That's your floor. $5 is the most you're willing to risk on this trade. Now, if the stock starts climbing up, and let's say hits 110, if it didn't go down, but your floor is still sitting at that 95, then you're exposed to a $15 fall. 

That makes no sense. So what we want is Claude to move up our floor to 105, which means if the stock dips and hits the new floor, you're still up $5 in profit, and you were protected the entire time. But what if the stock drops right out the gate, right? Well, that means it would just hit $95 and you'd sell it, and you're out $5, and that's your loss. 

Now, here's the important part. You're not stuck. You've still got that capital. 

Claude can now take that money and goes looking for the next setup. Maybe it's the same stock a week later at a better price. Maybe it's a completely different opportunity. 

The point is you lost a small portion that you're okay to lose and risk. Basically, you live to trade another day. And ideally, we find trades like this. 

So let's say the stock keeps climbing, and every time it does, Claude is going to drag the floor higher and higher. You can never fall back to where you started. It's basically now going to sell at 110.

So you get that $10 in profit, which is 10% gain. That's a trailing stop. You set the rules once, and Claude follows them every second of the day. 

You're always protected, and you're always locking in the gains. So when a trade doesn't work out, you move on fast with the most amount of money still in your pocket. Now, why am I telling you all of this? Because the worst thing you can really do is hand your AI a pile of money and be like, go figure it out. 

The rules aren't the limitation. That's the whole point. This is how you take what you know, your instincts, your risk tolerance, your read on the market, and you encode it. 

The same rules are true here. Claude can execute thousands of decisions faster than any human. It's executing your decisions, just running at the speed and discipline that you never could on your own. 

That's what makes this different from just letting AI loose. And I'll show you how to set this all up in the next portion. And to set this up, it's actually really simple. 

So I'm just back in my chat where I have been speaking with my Claude, and I'm just going to be speaking to it, right? And just to make it a little easier, if you guys wanted this, in my classroom, if you guys are already watching this, if you go to skills, you'll see I have a bunch of skills here. So this is the prompt we're essentially going to be speaking to our Claude, right? So let me just go to Claude. And right now, don't worry about it. 

If you want those docs, it's there, but you can follow along with me in this video. So I'm just going to speak to it. All right. 

So I want your help to actually schedule a trailing stop strategy on let's say Tesla, right? I want you to buy Tesla using Alpaca paper trading account by, I don't know, like 10 shares at the market price right now, and set up these rules. The floor, if the stock drops, let's say by 10%, sell everything. That's my stop loss. 

I don't want to lose more than that on this trade. The trailing floor, if the stock goes up 10% from what I paid, move my stop loss up, maybe move it up 5% below the current price. Every time it climbs, move another 5% up the floor again. 

So the floor only goes up, never down. And then I want you to also ladder in. If the stock drops, let's say by over 20, 30%, buy a bunch more shares, let's say 10 more shares. 

If it drops by let's say 20%, buy 20 shares. This way I'm getting better prices on the way down instead of just losing money. And after you set this up, show me a summary of every order and right after you place it. 

So I can confirm this looks right. Okay. So I word vomited some stuff there and let this finish and I'll show you what this looks like. 

So I see you just got done and it says this is the current price. And if I go back to my alpaca dashboard, I can see it set some price, it bought some Tesla, and then it even set a stop loss right here. Now, one more thing we need to do is make sure we go back here and be like, hey, can you set up during market hours every day that you're checking consistently when we need to move our floor up or need to make new stop losses or re-enter. 

Use the slash schedule to make sure we have that going and set your own schedules. So this just executed one trade. Now what I want is clock to basically be alive and keep looping and checking on a schedule like, hey, are these trades looking right? Do I need to re-enter? Do I need to move my floor up? All of that stuff. 

Normally we'd have to do it, but right now with the command I just gave it, it should be able to do it on its own. Okay. So it just got done and it says literally Tesla trailing stop monitor. 

And it's going to be doing that every five minutes from Monday to Friday, 9am. And it's going to keep checking. And just so you're clear on the left-hand side, if you hit, see this clock, if you hit this clock, it says scheduled. 

And if you open it up, these local tasks are already going to be running right here. You can see it already set the schedule for me. I didn't have to touch this. 

And if my computer is on, it's going to be running this on its own. Now we have basically made a trading bot. Now let's go through a couple different scenarios. 

Hey, so just briefly and really quickly, can you tell me what would happen if let's say Tesla shoots up to $500 randomly, what would you do? And right now I'm role-playing it just so you understand. And I encourage you to do this as well. So you understand what would happen in different scenarios and what would it actually do. 

And if you do really need to change its thinking and thought processes around, you would just be like, Hey, change this around. And right here, it just done. It says if Tesla shoots to 500 on the way up, the trailing stops kick in, trailing activates, your floor moves up, up, up, et cetera. 

And that's about it. This is a really cool way to do ladder buys. Those don't trigger at all. 

You see right now, I don't have any of them. So I'm going to be like, can you think about what are good ladder buys and make sure you set that up in the schedule and update the strategy inside our whole strategy of what we're trading right now. So as the price goes up, it buys in gradually. 

So we're always at somewhat of a profit and we're pretty safe in our buys. And just so you see, it even gave me the ladder levels of if it's negative 15%, it's going to buy 10. If it's 50%, it's going to buy 50.

You can always change this around, but this was really cool. Now that me without me having to do any of this stuff, Claude can just action it for me. Now this is all great, but the thing is we're still picking stocks ourselves. 

We choose Tesla because we like it, but that's a gut feeling. The biggest traders and the best traders in the world don't trade on gut feelings. They trade on information. 

So in the next level, we're going to be showing Claude where the smart money is. So Claude can actually make informed decisions. But what is smart money? Well, on wall street, there are people who move millions of dollars in a single trade.

When someone puts, let's say $50 million into a stock, they didn't really just do that of a gut feeling or flipping a coin. They have a lot of research teams and a lot of private data. They know something. 

These people are called whales. And when these whales make a big move, it leaves a trail like massive options orders, unusual volumes on a stock out of nowhere. And a group that does this a lot is surprisingly US politicians. 

But the nice part is that the members of Congress are required by law to report their stock trades. The data shows is that many of them consistently beat the market. They sit on committees, they regulate entire industries, they get briefed on policy changes before the public even hears about them. 

They know which companies are about to get a government contract and which ones may get investigated. But you can't see what they bought and follow them. And most people have no idea this data exists. 

But it's there and Claude can read it. But the thing is, we can't just tell Claude to go scour the internet for these hedge funds, trades and congressional filings and all that. There's millions of data points hitting the market every single day. 

No AI can really browse its way through all of that. But there are services that do this full time. These companies are scraping and organizing all this data around the clock. 

And the data is sitting there waiting to be tracked and updated every day. And what we need to do is plug Claude into that. And that's what this new skill and MCP does.

Think of it like a power outlet. The electricity, the insider information is running through those walls. And we basically plug our Claude into that so we can use it. 

These services have data flowing through their systems. And the MCP is the plug that connects Claude to their data. And once it's plugged in, Claude can pull from it anytime. 

It becomes a new skill. And Claude goes from being smart, but working with nothing, to being smart and seeing what the big players in the market see. Next, what we're going to do is give our Claude the power to access these services. 

And it's going to be super easy. So let's get into that. And just to emphasize why I'm so excited about this strategy I'm about to show you, this is me just backdating. 

Let's say a year ago, you were copying the same thing and the same strategy by copying the smart money. You can see if you were following the S&P 500, you were just buying and holding it, you would have made around, starting at a 50k account, you would have made around $57,750, which is around 15%. So you would have made 15% more money. 

But if you copied McCall, then you would have made $67,400 by the end of the year, which is a 34.8% return. You can see how these politicians have access to this insider information, and they can out-compete everybody. And that's what I'm going to show you how to do. 

And just to make sure our strategies are organized, what I'm going to do is go to another paper trading account. So right here, I'm going to use this Samin account, and I'm going to do the same thing. Okay, so I'm going to hit generate keys, I'm going to take all of this stuff, or I can just copy and paste this. 

And then I can go back to my cloud. And then what I'm going to do now is make a new session. So I hit new session, and I'm going to paste this in. 

And now what I'm going to do is the service we're going to use to track these politicians. If you go to Google, I'm going to do capital trades. And capital trades is a free service that you can be using to see which politician is trading what and what's going on. 

So I'm going to copy this URL, I'm going to go back to my cloud. And go right here. Okay, so now, by the way, the prompts are going to be in the description below. 

But right now, hey, so I'm trying to set up a copy trading bot. When I've also given you access to my alpaca account, I want you to make a new folder inside this folder. So we can have this running and have these schedules done. 

But what I want you to do is number one, find a politician who has been having really good success in the stock market currently and is actively trading. And then what I want you to do is copy their trades. Okay, so set up your current jobs and your schedules. 

So you're always looking and using capital trades to see what they're up to. And copy those trades, make sure you buy, sell, buy the same options that they knew, whatever you need to just copy them. And then we're going to be tracking that over time. 

All right. And you're going to be using the alpaca account that I just posted the image of. Great. 

I'm gonna hit bypass permissions, enter bypass mode, and then hit enter. All right, that was super easy. Let me wait for this to finish and we can see what's going on. 

Okay, so it just got done. And I see in my schedule, it's already set a schedule to see what these politicians are doing. And then I actually also asked it, who are you copy trading and why and it chose Michael Macau. 

All right, very interesting. And why is basically, okay. And why the algorithm picked him over the others, because it seems like he's very active right now. 

And he's the top trader. Interesting. The trades may be slightly stale, but that's the nature of how they disclose. 

We still get a lot of gains because mostly Congress can buy like two years out or something like that. So they don't do data trading and they're not allowed to do it. That's why even if we're a little late, because we know about it later, we can still make those gains. 

And just to reiterate, you can see this is a simulation for the year. If we started one year ago and did this exact same thing. If we copied this exact same strategy, this bot would have made an extra $9,650 in comparison to the S&P, which would have only made around $7,000. 

So that's a 2.2 X return over the S&P 500. And that's how these guys just stay so rich. It's kind of crazy. 

So with that out of the way, now I'm going to show you the third strategy, which is a strategy that really advanced people use, which means you can get paid no matter which direction the stock moves. And to understand that, I'm going to explain how options work. Okay, so what is an option? Well, an option is basically a contract when two people agree to do a deal. 

And let me show you this with something you already may know. Okay, so let's say you pay your car insurance company $100 a month and exchange, you get the right to file a claim if something goes wrong. And if you crash, the insurance covers it, you're protected. 

And if nothing happens, they keep your hundred bucks, they're basically getting paid to take on the risk. Now look at this exact same structure. What happens is you pay a premium to another trader where you get the right to buy or sell a stock at a locked price. 

Okay. And if the stock moves your way, you can exercise that contract and profit. If the stock doesn't move your way, the contract will expire, they keep your premium. 

It's the same deal, you basically paid for protection, they got paid for the risk. And here it is next to each other row by row. It's identical, the premium, the right to act the expiration date. 

And if nothing happens, the other side keeps your money. That's all an option is insurance on a stock. Okay. 

And to dive in, there are only two types of options. A call option gives you the right to buy a stock at a locked in price. Say Apple is at $200. 

You can buy a call option with a strike price of 210. That means if Apple goes to let's say 230 before your contract expires, you can buy it at 210 and pocket that $20 difference. If Apple stays below 210, your contract expires and you lose the premium you paid. 

That's your max loss. Think of it like putting a deposit on an apartment, you'll pay $500 to lock in the rent for $2,000 for 30 days. If the rent price jumps to $2,500, you got a deal.

If they don't, you lost that $500 deposit. And on the other side is a put option. The put option gives you the right to sell a stock at a locked in price. 

Say you own Apple at $200. You buy a put option with a strike price of $190. If Apple drops to $170, you can sell it at $190 instead of $170.

The put basically protected you from the drop. That's the insurance side. You paid a premium to protect yourself against the price drop. 

Why this is interesting is because with stocks and options, you can actually flip the table and become the insurance as well. So that is called selling options. So when you sell an option, you basically become the insurance company. 

You're the one that's collecting the premiums. So someone pays you for a contract. And most of the time, that contract expires without anything happening and you keep the money. 

And the cool part is the insurance companies make billions doing this. They collect premiums after premiums from millions of people and pay out on a small percentage of claims. The math basically works in their favor over time. 

And selling options basically work the same way where you collect a premium upfront. And if the stock doesn't hit the strike price by the expiration, your contract dies and you keep everything you were paid. And the wheel strategy is built on selling options. 

You are the insurance company. You collect premiums at every stage. And let me show you how that works.

OK, so let's walk through the wheel strategy with a real example with, let's say, Tesla. So Tesla is trading at $250. And let's say you really like the stock, but you're not paying 250 for it. 

You'd rather get it at, let's say, 230. So if you sell a put at the 230 strike and for making that promise for saying, I'll buy Tesla at 230 if the price drops there, someone is going to hand you $5 per share. That's $500 in your pocket right now just for agreeing to do a deal you already wanted.

Now, two things can happen. Tesla can stay above 230, which means the contract might expire. Nobody makes you buy anything and you get to keep the $500 and you can do it again the next week.

The other scenario is Tesla drops below 230 and you have to buy it. But remember, you collected $500 before already. So your real cost isn't 230, it's 225. 

You got Tesla cheaper than anyone else and you wanted it anyways. OK, so stage two, let's say Tesla does drop and you get a sign, which means you have to buy the Tesla shares. Now you own 100 shares at an effective cost of 225.

Most people would be upset.

(This file is longer than 30 minutes. Go Unlimited at https://turboscribe.ai/ to transcribe files up to 10 hours long.)