# -*- coding: utf-8 -*-
"""
Created on Sun Oct 20 16:10:45 2019

@author: William
"""

import csv 

import numpy as np
import pandas as pd
import xml.etree.ElementTree as et
from lxml import etree



def getter(n,lst=None):
    if lst is None:
        lst=[n.tag]
    for ch in n.getchildren():
        if len(ch.getchildren()) == 0:
            
            yield lst + [ch.tag]
            
                
                
        else:
            pop = lst + [ch.tag]
            yield from getter(ch,lst=pop)
            
def converter(n):
    text_concat=[]
    for ch in n.getchildren():
        if not ch.tag is etree.Comment:
            if len(ch.getchildren()) == 0:
                if not ch.text is None and ch.tag != 'text':
                    n.set(ch.tag,ch.text)
                elif not ch.text is None and ch.tag =='text':
                    text_concat.append(ch.text)
                    
                n.remove(ch)
                
            else:
                            
                n.replace(ch,converter(ch))
        else:
            n.remove(ch)
    if len(text_concat) != 0:            
        n.set('text','\n'.join(text_concat))
    return n
def prettify(x):
    print(etree.tostring(x,pretty_print=True,encoding='unicode'))


def monster_df_gen(root):
    
    monster_list = root.xpath("//monster")
    monster_dict_list = []
    
    for monster in monster_list:
        comb, traits,actions,legends = statblock_gen(converter(monster))
        monster.set('comb_text',comb)
        monster.set('traits_text',traits)
        monster.set('actions_text',actions)
        monster.set('legends_text',legends)
        
        key_list = ['cr','name','size','type','alignment','environment','comb_text','traits_text','actions_text','legends_text']
        
        if any([x not in monster.attrib.keys() for x in key_list]):
            for k in [x for x in key_list if not x in monster.attrib.keys()]:
                monster.set(k,'-')
        
        monster_dict_list.append({k:v for k,v in monster.attrib.items() if k in key_list})
    monster_df = pd.DataFrame(monster_dict_list)
    return monster_df




def stat_fmt(df):
    stats = df[['str','dex','con','int','wis','cha']].T
    stats['mod'] = np.floor((stats.val.astype('int')-10)/2).astype('int')
    stats['mod_str'] = [f'(+{x})' if x >= 0 else f'({x})' for x in stats['mod']]
    stats['text'] = stats.val.astype('str') + ' ' + stats.mod_str
    stat_text = stats[['text']].T.to_string(index=False,justify='center',header=[x.upper() for x in stats[['text']].T.columns])
    stat_text = '\n'.join([stat_text.split('\n')[0],
    '='*len(stat_text.split('\n')[0]),
    stat_text.split('\n')[1]])
    return stat_text

#other_info_cols = ['resist','vulnerable','immune','senses','passive','languages','cr']



def trait_action_fmt(monster):
    traits = [x for x in monster if x.tag == 'trait']
    actions = [x for x in monster if x.tag == 'action']
    legends = [x for x in monster if x.tag == 'legendary']
    traits_text = '\n' + '\n'.join([trait_fmt(x) for x in traits])
    actions_text = '\n' + '\n'.join([trait_fmt(x) for x in actions])
    legends_text = '\n' + '\n'.join([trait_fmt(x) for x in legends])
    esc_undl = '\_'
    
    #traits_actions = f'''__**Traits**{esc_undl*50}__{traits_text}
    #__**Actions**{esc_undl*50}__{actions_text}'''
    traits = f'__**Traits**{esc_undl*50}__{traits_text}'
    traits = f'{traits_text}'
    actions = f'__**Actions**{esc_undl*50}__{actions_text}'
    legends = f'__**Legendary Actions**{esc_undl*50}__{legends_text}'
    if legends_text == '\n':
        legends = ''
    
    
    return traits,actions,legends

        
def trait_fmt(t):
    if t.get('attack') is None:
        return f"> **{t.get('name')}.** {t.get('text')}\n"
    else:
        return f"> **{t.get('name')}.** {t.get('text')}\n> {atk_fmt(t)}\n"


def atk_fmt(t):
    atk_split = t.get('attack').split('|')
    atk_dict = {'name': atk_split[0],
                'to_hit': atk_split[1],
                'dmg': atk_split[2]
        }
    if atk_dict['to_hit'] != '':
        return f'''```ml\n> Attack Roll: !1d20+{atk_dict['to_hit']}\t Damage Roll: !{atk_dict['dmg']}\t```'''
    else:
        return f'''```ml\n> Damage Roll: !{atk_dict['dmg']}\t```'''
    
def statblock_gen(monster):

    
    size_dict = {'L':'Large',
                 'M':'Medium',
                 'S':'Small',
                 'H': 'Huge',
                 'G':'Giant',
                 'T':'Tiny',
                 'C':'Colossal'
                 }
    
    df = pd.DataFrame(monster.attrib.items(),columns=['var','val']).set_index('var').T
    header = f'''**{monster.get('name')}**
*{size_dict.get(monster.get('size'))} {monster.get('type')}, {monster.get('alignment')}*
```asciidoc
Armor Class :: {monster.get('ac')}
Hit Points :: {monster.get('hp')}
Speed :: {monster.get('speed')}
```'''
    
    stats = f'''```asciidoc
{stat_fmt(df)}
```'''
    if not monster.get('save') is None:
        saves = f"\nSaving Throws :: {monster.get('save')}"
    else:
        saves = ''
        
    if not monster.get('skill') is None:
        skills  = f"\nSkills :: {monster.get('skill')}"
    else:
        skills = ''
    
    if saves+skills != '':
        skills = f'''```asciidoc{saves}{skills}
```'''
    
    if monster.get('immune') is None:
        immunities = ''
    else:
        immunities = f"\nDamage Immunities :: {monster.get('immune')}"
        
    if monster.get('vulnerable') is None:
        vulnerabilities = ''
    else:
        vulnerabilities = f"\nDamage Vulnerabilities :: {monster.get('vulnerable')}"
    
    if monster.get('resist') is None:
        resistances = ''
    else:
        resistances = f"\nDamage Resistances :: {monster.get('resist')}"
        
    other_info = f'''```asciidoc{vulnerabilities}{immunities}{resistances}
Senses :: {monster.get('senses')}, passive Perception {df.passive.val}
Languages :: {monster.get('languages')}
Challenge :: {monster.get('cr')}
Environment :: {monster.get('environment')}
```'''
    traits,actions,legends = trait_action_fmt(monster)
    
    
    comb = f'''{header}
{stats}{skills}
{other_info}'''.replace('```\n```','``````')

    
    return comb,traits,actions,legends

def get_discord_monster_message(monster):
    messages=[]
    for x in ['comb_text','traits_text','actions_text','legends_text']:
        if len(messages) ==0:
            messages.append(monster.loc[x])
        elif len('\n'.join([messages[-1],monster.loc[x]])) < 2000:
            messages[-1] += monster.loc[x]
        else:
            messages.append(monster.loc[x])
    
    return messages
            
#%%
if __name__ == '__main__':
    comp = 'CoreRulebooksAndSupplements.xml'


    f = open(comp,'rb').read()
    root = etree.XML(f)
    doc = etree.ElementTree(root)
    monster_df = monster_df_gen(root)
    monster_df.to_pickle('monsters.pkl')

#%%



#%%

#%%

#%%

