#seinfeldbot.py

#Seinfeld Trading Card Game Bot for Discord
#-roll for random character once per hour with ability to claim character if desired
#-trade characetrs with other users
#-battle other users to gain points that can be used for bonus rolls
#-generate a random Seinfeld quote!S

import os
import random
import json
import math
from turtle import title

import discord
from dotenv import load_dotenv

from discord.ext import commands

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

intents=discord.Intents.all()

#set bot's command prefix
bot = commands.Bot(command_prefix='!', intents=intents)

#Generates message when bot joins server
@bot.event
async def on_ready():
    guild = discord.utils.get(bot.guilds, name=GUILD)

    print(
        f'{bot.user} is connected to the following server:\n'
        f'{guild.name}(id: {guild.id})'
    )

#generates message when a user joins the server
@bot.event
async def on_member_join(member):
    #access user database
    f = open('users.json')
    database = json.load(f)
    f.close()
    not_in_db = True

    #checks if user is already in database
    for entry in database['user_database']:
        if entry['user_id'] == member.id:
            not_in_db = False
    
    #creates an entry in the database for the new user to keep track of characters claimed and points achieved
    if not_in_db:
        database['user_database'].append({'user_id': member.id, 'user_name': f'{member}', 'points': 0, 'chars_claimed': []})
        data = database
        with open("users.json", "w") as file:
            json.dump(data, file, indent=4)

    channel = bot.get_channel(1099755929626488864)
    await channel.send(f'{member} joined the server!')

#Generates message when user leaves the server
@bot.event
async def on_member_remove(member):
    #access character database
    sfdb_file = open('sfdata.json')
    sf_database = json.load(sfdb_file)
    sfdb_file.close()

    #access user database
    users_file = open('users.json')
    user_database = json.load(users_file)
    users_file.close()

    #remove user's claim from character database so characters become claimable again
    for entry in sf_database['seinfeld_database']:
        if(entry["claimed_by"] == member.id):
            entry["claimed_by"] = ""
    data = sf_database
    with open("sfdata.json", "w") as file:
        json.dump(data, file, indent=4)

    #remove user data from user database
    index = 0
    for entry in user_database['user_database']:
        if entry["user_id"] == member.id:
            del user_database['user_database'][index]
            data = user_database
            with open("users.json", "w") as file:
                json.dump(data, file, indent=4)
            break
        index = index + 1

    channel = bot.get_channel(1099755929626488864)
    await channel.send(f'{member} has left the server.')  

#generates a reandom Seinfeld quote
@bot.command(name='quote', help='Responds with a random quote from Seinfeld')
async def quote(ctx):
    #access quote database
    quotes_file = open('quotes.json')
    quotes_database = json.load(quotes_file)
    quotes_file.close()

    num_quotes = 0

    #get the number of quotes in the database
    for quote in quotes_database['quotes']:
        num_quotes += 1
    
    #generate a random index to obtain random quote
    index = random.randint(0,num_quotes-1)

    #get quote from array of quotes using generated index
    selected_quote = quotes_database['quotes'][index]
    await ctx.send(selected_quote)

#Roll for a random Seinfeld Character
@bot.command(name='rs', help='Roll for a random Seinfeld Character')
@commands.cooldown(1, 3600, commands.BucketType.user)
async def roll(ctx):
    #access character database
    sfdb_file = open('sfdata.json')
    sf_database = json.load(sfdb_file)
    sfdb_file.close()
    data = ""
    dataSize = 0

    #get the number of characters in the database
    for db_entry in sf_database['seinfeld_database']:
        dataSize += 1
    
    #get random character from the list of characters
    index = random.randint(0, dataSize - 1)
    c_name = sf_database['seinfeld_database'][index]['char_name']
    c_desc = sf_database['seinfeld_database'][index]['char_description']
    img_url = sf_database['seinfeld_database'][index]['char_img']
    claimed_by = sf_database['seinfeld_database'][index]['claimed_by']
    battle_stat = sf_database['seinfeld_database'][index]['battle_stat']

    #send message showing generated character
    embed=discord.Embed(title=c_name, color=0x00AE86, description=f'{c_desc} \n\nBattle Stat:  {battle_stat}')
    embed.set_image(url=img_url)

    #if character already claimed, show that it is claimed in message
    if(claimed_by):
        embed.set_footer(text=f'Claimed by: {bot.get_user(claimed_by)}')
    msg = await ctx.send(embed=embed)

    try:
        #wait 10 seconds for a claim from a user. User can claim character by reacting with an emoji
        reaction, user = await bot.wait_for('reaction_add', timeout=10.0, check=lambda r, u: r.message.id == msg.id)

        #if embed has footer, then character already claimed
        if(reaction.message.embeds[0].footer.text):
            await ctx.send(f'{reaction.message.embeds[0].title} already claimed')
        else:
            #if not claimed, set claimed to user who reacted with reaction window
            msg = reaction.message
            embed = msg.embeds[0]
            embed.set_footer(text=f'Claimed by: {user}')
            
            #file needs to be reopened so that database data is up to date when storing claimed user
            #--This avoids an issue where if the database wasn't reopened and the claim occurs, it can overwrite a claim from a roll that happened at or near the same time
            sfdb_file = open('sfdata.json')
            sf_database = json.load(sfdb_file)
            sfdb_file.close()

            #access user database
            users_file = open('users.json')
            user_database = json.load(users_file)
            users_file.close()
            
            #update seinfeld character database with new user claim
            for entry in sf_database['seinfeld_database']:
                if(entry['char_name'] == embed.title):
                    entry["claimed_by"] = user.id
            data = sf_database
            with open("sfdata.json", "w") as file:
                json.dump(data, file, indent=4)

            #update user database with new user claim
            for entry in user_database['user_database']:
                if(entry['user_id'] == user.id):
                    entry['chars_claimed'].append(f'{c_name}')
            data = user_database
            with open("users.json", "w") as file:
                json.dump(data, file, indent=4)

            await msg.edit(embed=embed)
            await ctx.send(f'{user.mention} successfully claimed {embed.title}')
    except TimeoutError:
        print('Claim window timed out')

#if user tries to roll for random character before their roll cooldown is over, error message is sent notify the user
@roll.error
async def cooldown_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f'Roll available again in {round(error.retry_after/60, 1)} min(s)')

#Roll for a random Seinfeld Character using points
@bot.command(name='rsp', help='Roll for a random Seinfeld Character using 100 points')
async def rollpoints(ctx):
    #access user database
    users_file = open('users.json')
    user_database = json.load(users_file)
    users_file.close()

    index = 0
    user_index = -1

    #find the user's entry in the user database
    for user in user_database['user_database']:
        if user['user_id'] == ctx.author.id:
            user_index = index
        index += 1

    #check if the user has enough points to execute the roll
    if user_database['user_database'][user_index]['points'] < 100:
        await ctx.send(f'Cannot roll - {ctx.author.mention} does not have enough points')
    else:
        #if roll goes through, updates the users points
        user_database['user_database'][user_index]['points'] -= 100
        with open("users.json", "w") as file:
            json.dump(user_database, file, indent=4)

        await ctx.invoke(bot.get_command('rs'))

#A command accessible for the admin of the server only that wipes clean all claims in databases. This was used for testing purposes
@bot.command(name='wipe', help='Wipes all claims in database (admin command)')
async def WriteDB(ctx):
    if(ctx.author == ctx.guild.owner):
        #access the seinfeld character database
        sfdb_file = open('sfdata.json')
        sf_database = json.load(sfdb_file)
        sfdb_file.close()

        #access the user database
        users_file = open('users.json')
        user_database = json.load(users_file)
        users_file.close()

        #re-write the seinfeld database with wiped claims
        for entry in sf_database['seinfeld_database']:
            entry["claimed_by"] = 0
        data = sf_database
        with open("sfdata.json", "w") as file:
            json.dump(data, file, indent=4)
        
        #re-write the user database with wiped claims
        for entry in user_database['user_database']:
            entry["chars_claimed"] = []
        data = user_database
        with open("users.json", "w") as file:
            json.dump(data, file, indent=4)
    
        await ctx.send('claims wiped')


#command to let players view the profile of points and currently claimed characters
@bot.command(name='prof', help='View your profile with list of collected characters')
async def ViewProfile(ctx):
    #access the user database
    users_file = open('users.json')
    user_database = json.load(users_file)
    users_file.close()

    #access the seinfeld character database
    sfdb_file = open('sfdata.json')
    sf_database = json.load(sfdb_file)
    sfdb_file.close()

    characters = ""
    points = 0

    #get the user's profile from database and formats a list of the characters that they have claimed along with their battle powers
    for entry in user_database['user_database']:
        if entry['user_id'] == ctx.author.id:
            for char in entry['chars_claimed']:
                char_power = 0
                for sfchar in sf_database['seinfeld_database']:
                    if sfchar['char_name'] == char:
                        char_power = sfchar['battle_stat']
                characters += char + ' ' + f'{char_power}\n'
            #get the user's current points
            points=entry['points']
            break
    
    #get the number of characters the user has claimed and separate into pages the user can cycle through (10 characters per page)
    chars_to_display = ''
    char_list = characters.split('\n')
    num_chars = len(char_list)
    page_index = 1
    num_pages = math.ceil(num_chars/10)

    for i in range(10):
        if i < num_chars:
            chars_to_display += char_list[i] + '\n'
        else:
            break

    #create the message showing the user's name, profile picture, points, and first 10 characters claimed 
    embed=discord.Embed(title=ctx.author, color=0x000080, description='')
    embed.add_field(name='Points', value=points, inline=False)
    embed.add_field(name='Characters', value=chars_to_display, inline=False)
    embed.set_thumbnail(url=ctx.author.avatar)

    #if user has more than 10 characters, display the page numbers
    if num_pages > 1:
        embed.set_footer(text=f'Page {page_index}/{num_pages}')

    msg = await ctx.send(embed=embed)

    #if the user has more than 10 characters, user has 2 minutes to press the arrow buttons on the message to cycle through the pages of their characters
    if num_pages > 1:
        await msg.add_reaction('⬅️')
        await msg.add_reaction('➡️')

        while True:
            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=120.0, check=lambda r, u: r.message.id == msg.id and u.id == ctx.author.id)

                #if left arrow is clicked, go to previous character page
                if str(reaction.emoji) == '⬅️':
                    print('Left arrow was clicked')
                    
                    page_index -= 1

                    #cycle to last page if currently on first
                    if page_index < 1:
                        page_index = num_pages
                        
                    chars_to_display = ''

                    #get characters to diplay
                    for i in range(10):
                        if ((page_index-1) * 10) + i < num_chars:
                            chars_to_display += char_list[((page_index-1) * 10) + i] + '\n'
                        else:
                            break

                    #display the set of characters corresponding to the page number for the user
                    embed=discord.Embed(title=ctx.author, color=0x000080, description='')
                    embed.add_field(name='Points', value=points, inline=False)
                    embed.add_field(name='Characters', value=chars_to_display, inline=False)
                    embed.set_thumbnail(url=ctx.author.avatar)
                    embed.set_footer(text=f'Page {page_index}/{num_pages}')

                    await msg.edit(embed=embed)

                    await msg.remove_reaction(reaction, user)
                #if right arrow is clicked, go to next character page
                elif str(reaction.emoji) == '➡️':
                    print('Right arrow was clicked')

                    page_index += 1

                    #cycle to first page if currently on last
                    if page_index > num_pages:
                        page_index = 1
                        
                    chars_to_display = ''

                    #get characters to diplay
                    for i in range(10):
                        if ((page_index-1) * 10) + i < num_chars:
                            chars_to_display += char_list[((page_index-1) * 10) + i] + '\n'
                        else:
                            break

                    #display the set of characters corresponding to the page number for the user
                    embed=discord.Embed(title=ctx.author, color=0x000080, description='')
                    embed.add_field(name='Points', value=entry['points'], inline=False)
                    embed.add_field(name='Characters', value=chars_to_display, inline=False)
                    embed.set_thumbnail(url=ctx.author.avatar)
                    embed.set_footer(text=f'Page {page_index}/{num_pages}')

                    await msg.edit(embed=embed)

                    await msg.remove_reaction(reaction, user)
                else:
                    print('Something else happened')

            except TimeoutError:
                print('Profile command timed out')
    
#command to allow users to trade characters
@bot.command(name='trade', help='Initiate trade with another user EX: !trade "Jerry Seinfeld" "Elaine Benes"')
async def Trade(ctx, c_offered, c_wanted):
    #access the seinfeld character database
    sfdb_file = open('sfdata.json')
    sf_database = json.load(sfdb_file)
    sfdb_file.close()

    bot_msg = ""
    t_offer_good = False    #variable for checking validity of trade

    #check if the character the trader is offering is claimed by the user, if not the trade will fail
    for entry in sf_database['seinfeld_database']:
        if entry['char_name'] == c_offered:
            if entry['claimed_by'] == ctx.author.id:
                t_offer_good = True
            else:
                bot_msg = f'Trade cannot initiate - {ctx.author.mention} does not own {c_offered}'
            break

    if len(bot_msg) == 0 and not t_offer_good:
        bot_msg = 'trade cannot initiate - character offered does not exist in the database'

    #if trade offer is good, check if the wanted character is claimed by anyon on the server, if not the trade will fail
    if t_offer_good:
        for entry in sf_database['seinfeld_database']:
            if entry['char_name'] == c_wanted:
                if entry['claimed_by'] > 0:
                    claimed_by = entry['claimed_by']
                    user = bot.get_user(claimed_by)
                    bot_msg = f'{ctx.author.mention} would like to trade {c_offered} for {user.mention}\'s {c_wanted}'
                else:
                    bot_msg = f'Trade cannot initiate - {c_wanted} not claimed by anyone in this server'
                break

    if len(bot_msg) == 0:
        bot_msg = 'trade cannot initiate - character wanted does not exist in the database'

    #send resulting message
    msg = await ctx.send(bot_msg)

    try:
        #allow tradee 30 seconds to respond and accept trade by providing a reaction to the trade message
        reaction, user_react = await bot.wait_for('reaction_add', timeout=30.0, check=lambda r, u: r.message.id == msg.id and u.id == user.id)
        print('Trade accepted!')

        #open database again to ensure database wasn't altered between trade request being sent and trade request being accepted
        sfdb_file = open('sfdata.json')
        sf_database = json.load(sfdb_file)
        sfdb_file.close()

        trade_good = 0
        index = 0
        i_trader = -1
        i_tradee = -1

        #double check that users in trade request own respective characters
        for entry in sf_database['seinfeld_database']:
            if entry['char_name'] == c_offered:
                if entry['claimed_by'] == ctx.author.id:
                    trade_good += 1
                    i_trader = index
            if entry['char_name'] == c_wanted:
                if entry['claimed_by'] == user_react.id:
                    trade_good += 1
                    i_tradee = index
            index += 1

        #if trade_good = 2, then both parties are able to accept trade and trade occurs via altering database data
        if trade_good == 2:
            #trade succeeds and suer claims are swapped in seinfeld database
            sf_database['seinfeld_database'][i_trader]['claimed_by'] = user_react.id
            sf_database['seinfeld_database'][i_tradee]['claimed_by'] = ctx.author.id

            data = sf_database

            #write the updated claims to th database
            with open("sfdata.json", "w") as file:
                json.dump(data, file, indent=4)

            #access the user database
            users_file = open('users.json')
            user_database = json.load(users_file)
            users_file.close()

            index = 0
            i_trader = -1
            i_trader_char = -1
            i_tradee = -1
            i_tradee_char = -1

            #find the tader and tradee's profiles in the database and the users' indices and the indices of the traded characters in their respective character lists
            for entry in user_database['user_database']:
                if entry['user_id'] == ctx.author.id:
                    index_char = 0
                    for char in entry['chars_claimed']:
                        if char == c_offered:
                            i_trader = index
                            i_trader_char = index_char
                            break
                        index_char += 1
                if entry['user_id'] == user_react.id:
                    index_char = 0
                    for char in entry['chars_claimed']:
                        if char == c_wanted:
                            i_tradee = index
                            i_tradee_char = index_char
                            break
                        index_char += 1
                index += 1

            #swap the characters being traded in their respective character lists
            user_database['user_database'][i_trader]['chars_claimed'][i_trader_char] = c_wanted
            user_database['user_database'][i_tradee]['chars_claimed'][i_tradee_char] = c_offered

            data = user_database

            #write the updated data to the user database
            with open("users.json", "w") as file:
                json.dump(data, file, indent=4)

            await ctx.send(f'Trade Successful! - {ctx.author.mention} traded {c_offered} for {user.mention}\'s {c_wanted}')         
    except TimeoutError:
        print('Trade window timed out')    

#command to allow users to battle each other with their characters
@bot.command(name='battle', help='Initiate a battle with another user EX: !battle "Jerry Seinfeld"')
@commands.cooldown(1, 3600, commands.BucketType.user)
async def Battle(ctx, c_battle_1):
    #access the seinfeld database
    sfdb_file = open('sfdata.json')
    sf_database = json.load(sfdb_file)
    sfdb_file.close()

    bot_msg = ""
    battle_initiate = False
    index = 0
    i_battle_1 = -1
    i_battle_2 = -1
    
    #check to make sure the user initiating the battle owns the character they are trying to battle with
    for entry in sf_database['seinfeld_database']:
        if entry['char_name'] == c_battle_1:
            if entry['claimed_by'] == ctx.author.id:
                bot_msg = f'{ctx.author.mention} would like to battle with {c_battle_1}'
                i_battle_1 = index
                battle_initiate = True
            else:
                #if user doesn't own specified character, then battle command fails
                bot_msg = f'Battle cannot initiate - {ctx.author.mention} does not own {c_battle_1}'
            break
        index += 1

    #if user specifies a non-existent character, then battle command fails
    if len(bot_msg) == 0:
        bot_msg = f'battle cannot initiate - character {ctx.author.mention} chose to battle with does not exist in the database'

    msg = await ctx.send(bot_msg)

    #if battle initiation succeeds, create message and give a user 60 seconds to respond and accept battle
    if battle_initiate:
        try:
            reply = await bot.wait_for('message', timeout=60.0, check=lambda m: m.reference is not None and m.reference.message_id == msg.id and m.author.id != ctx.author.id)
            print('Battle accepted!')

            bot_msg = ''
            index = 0
            battle_accept = False

            #if battle is accepted, check that the user accepting the battle owns the character they are trying to battle with
            for entry in sf_database['seinfeld_database']:
                if entry['char_name'] == reply.content:
                    if entry['claimed_by'] == reply.author.id:
                        bot_msg = f'{reply.author.mention} accepted {ctx.author.mention}\'s request for battle with {reply.content}'
                        i_battle_2 = index
                        battle_accept = True
                    else:
                        #if user doesn't own specified character, then battle command fails
                        bot_msg = f'battle failed - {reply.author.mention} does not own {reply.content}'
                    break
                index += 1

            #if user specifies a non-existent character, then battle command fails
            if len(bot_msg) == 0:
                bot_msg = f'battle failed - character {reply.author.mention} chose to battle with does not exist in the database'

            await ctx.send(bot_msg)

            #if battle is successfully accepted, execute attacks
            if battle_accept:
                #get player 1's attack power by randomly generating a number from 0 to the battle power of the character they selected
                player_1_power = random.randint(0, sf_database['seinfeld_database'][i_battle_1]['battle_stat'])
                await ctx.send(f'{ctx.author.mention} rolled a(n) {player_1_power} with {c_battle_1}')

                #get player 2's attack power by randomly generating a number from 0 to the battle power of the character they selected
                player_2_power = random.randint(0, sf_database['seinfeld_database'][i_battle_2]['battle_stat'])
                await ctx.send(f'{reply.author.mention} rolled a(n) {player_2_power} with {reply.content}')

                #if player 1 gets a higher attack power than player 2, player 1 wins and gains points equivalent to 10 times the difference of the battle powers generated during battle
                if player_1_power > player_2_power:
                    player_1_points = (player_1_power - player_2_power) * 10
                    if sf_database['seinfeld_database'][i_battle_1]['battle_stat'] < sf_database['seinfeld_database'][i_battle_2]['battle_stat']:
                        player_1_points = player_1_points * (sf_database['seinfeld_database'][i_battle_2]['battle_stat'] - sf_database['seinfeld_database'][i_battle_1]['battle_stat'] + 1)

                    #access the user database
                    users_file = open('users.json')
                    user_database = json.load(users_file)
                    users_file.close()

                    index = 0
                    player_1_index = -1

                    #get player 1's profile entry from user database
                    for entry in user_database['user_database']:
                        if entry['user_id'] == ctx.author.id:
                            player_1_index = index
                            break
                        index += 1

                    #add points to player 1's points from database
                    user_database['user_database'][player_1_index]['points'] += player_1_points
                    data = user_database

                    #re-write the updated data back into the user database
                    with open("users.json", "w") as file:
                        json.dump(data, file, indent=4)

                    #display message indicating winner and points won
                    bot_msg = f'{ctx.author.mention} won the battle and gained {player_1_points} points!'
                #if player 2 gets a higher attack power than player 1, player 2 wins and gains points equivalent to 10 times the difference of the battle powers generated during battle
                elif player_2_power > player_1_power:
                    player_2_points = (player_2_power - player_1_power) * 10
                    if sf_database['seinfeld_database'][i_battle_2]['battle_stat'] < sf_database['seinfeld_database'][i_battle_1]['battle_stat']:
                        player_2_points = player_2_points * (sf_database['seinfeld_database'][i_battle_1]['battle_stat'] - sf_database['seinfeld_database'][i_battle_2]['battle_stat'] + 1)

                    #access the user database
                    users_file = open('users.json')
                    user_database = json.load(users_file)
                    users_file.close()

                    index = 0
                    player_2_index = -1

                    #get player 2's profile entry from user database
                    for entry in user_database['user_database']:
                        if entry['user_id'] == msg.author.id:
                            player_2_index = index
                            break
                        index += 1

                    #add points to player 2's points from database
                    user_database['user_database'][player_2_index]['points'] += player_2_points
                    data = user_database

                    #re-write the updated data back into the user database
                    with open("users.json", "w") as file:
                        json.dump(data, file, indent=4)

                    #display message indicating winner and points won
                    bot_msg = f'{reply.author.mention} won the battle and gained {player_2_points} points!'
                else:
                    bot_msg = 'It\'s a draw!'

            await ctx.send(bot_msg)
        except TimeoutError:
            print('Battle window timed out')

#if user tries to battle again before their battle cooldown is over, error message is sent notify the user
@Battle.error
async def cooldown_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f'Battle available again in {round(error.retry_after/60, 1)} min(s)')

bot.run(TOKEN)