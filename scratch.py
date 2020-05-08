# -*- coding: utf-8 -*-
"""
Created on Sat May  2 13:40:58 2020

@author: William
"""

import os, json,codecs,re
from monster_parse import *
from pathlib import Path
#%%
def frac_2_float(fraction):
    numerator, denominator = fraction.split('/')
    return float(numerator) / float(denominator)


def score_parse(d):
    skill_renames = {
        'str':'strength',
        'dex':'dexterity',
        'con':'constitution',
        'int':'intelligence',
        'wis':'wisdom',
        'cha':'charisma',
        'cr':'challenge_rating'
        }
    if not 'cr' in d.keys():
        d['cr'] = '0'
    
    
    for k,v in skill_renames.items():
        try:
            val = d.pop(k)
            d[v] = int(val)
        except:
            if k == 'cr': d[v] = frac_2_float(val)
    
    



def skill_parse(d):
    skills = d['skill'].lower().split(', ')
    
    if any([len(y.split(' ')) > 2 for y in skills]):
        d['skills'] = d.pop('skill')
        return
    
    for x in skills:
        skill,val = x.split(' ')
        d[skill] = int(val)
    del d['skill']

def text_field_rename(d):
    rename_dict = {'vulnerable':'damage_vulnerabilities',
                   'resist':'damage_resistances',
                   'conditionImmune':'condition_immunities',
                   'immune':'damage_immunities'
                   }
    for k,v in rename_dict.items():
        if d.get(k) is None:
            d[v] = ''
        else:
            d[v] = d.pop(k)
            
def ac_parse(d):
    
    try:
        armor_class = int(d['ac'])
    except:
        armor_class,armor_type = d.get('ac').split(' ',1)
        armor_class = int(armor_class)
        
        d['special_abilities'].append({'name':'Armor Type','desc':armor_type,'attack_bonus':0})
        
    d['armor_class'] = armor_class
    del d['ac']

def hp_parse(d):
    
    if ' ' in d['hp']:
        hit_points,hit_dice = d['hp'].split(' ',1)
        hit_dice = hit_dice[1:-1]
    else:
        hit_points = d['hp']
        hit_dice = '0d0'
    
    if '+' in hit_dice:
        hit_dice = hit_dice.split('+')[0]
    elif '-' in hit_dice:
        hit_dice = hit_dice.split('-')[0]
    
    
    d['hit_points'] = int(hit_points)
    d['hit_dice'] = hit_dice
    del d['hp']

def sense_parse(d):
    senses = d.get('senses')
    if senses is None:
        d['senses'] = f"passive Perception {d['passive']}"
    else:
        d['senses'] = f"{senses}, passive Perception {d['passive']}"
    del d['passive']

def save_parse(d):
    skill_renames = {
        'str':'strength',
        'dex':'dexterity',
        'con':'constitution',
        'int':'intelligence',
        'wis':'wisdom',
        'cha':'charisma',
        'cr':'challenge_rating'
        }
    save_dict ={}
    for x in d['save'].lower().split(', '):
        k,v = x.split(' ')
        save_dict[f"{skill_renames[k]}_save"] = int(v)
    
    d.update(save_dict.items())
    del d['save']

def attack_helper(temp,x):
    name,attack_bonus,dmg = x.get('attack').split('|')
    
    if '+' in dmg:
        #damage_dice,damage_bonus = dmg.split('+')
        damage_dice = '+'.join([x for x in dmg.split('+') if 'd' in x])
        damage_bonus = sum([int(x) for x in dmg.split('+') if not 'd' in x])
    elif '-' in dmg:
        damage_dice,damage_bonus = dmg.split('-')
    else:
        damage_bonus = 0
        damage_dice = dmg
    
    ##making sure the attack bonus is not just missing
    if attack_bonus in ['',' ']:
        m = re.search('.*: \+(\d+) to hit,.*',temp['desc'])

        if not m is None:
            if len(m.groups()) == 1:
                attack_bonus = int(m.groups()[0])
        else:
            attack_bonus = 0
    
    temp['attack_bonus'] = int(attack_bonus)
    temp['damage_dice'] = damage_dice
    temp['damage_bonus'] = int(damage_bonus)
    

def size_fix(d):
    size_dict = {
        't':'Tiny',
        's':'Small',
        'm':'Medium',
        'l':'Large',
        'h':'Huge',
        'g':'gargantuan'
        }
    d['size'] = size_dict.get(d['size'].lower())
    
def monster_dict_refmt(monster):
    '''
    
    Parameters
    ----------
    monster : xml object from converter() fn in monster_parse
        Describes a monster statblock, originally formatted for Fight Club 5th Edition.

    Returns
    -------
    xml_dict : dict
        JSON dict in the same format as the saved JSONs used by bobifle to create tokens:
            https://github.com/bobifle/5e-database

    '''
    
    dict_lists ={'special_abilities':[],'actions':[],'legendary_actions':[]}
    
    for x in monster:
        
        if x.tag == 'trait':
            temp = {}
            temp['name'] = x.get('name')
            temp['desc'] = x.get('text')
            
            if x.get('attack') is None:
                temp['attack_bonus'] = 0
            else:
                attack_helper(temp,x)
                
            dict_lists['special_abilities'].append(temp)
        elif x.tag == 'action':
            temp = {}
            temp['name'] = x.get('name')
            temp['desc'] = x.get('text')
            
            
            if x.get('attack') is None:
                temp['attack_bonus'] = 0
            else:
                attack_helper(temp,x)
                
                dict_lists['actions'].append(temp)
        elif x.tag == 'legendary':
            temp = {}
            temp['name'] = x.get('name')
            temp['desc'] = x.get('text')
            
            
            if x.get('attack') is None:
                temp['attack_bonus'] = 0
            else:
                attack_helper(temp,x)
                
                dict_lists['legendary_actions'].append(temp)
    
    xml_dict = {**monster.attrib,**dict_lists}
    
    score_parse(xml_dict)
    if not xml_dict.get('skill') is None:
        skill_parse(xml_dict)
        
    if not xml_dict.get('save') is None:
        save_parse(xml_dict)
        
    text_field_rename(xml_dict)
    ac_parse(xml_dict)
    hp_parse(xml_dict)
    sense_parse(xml_dict)
    if len(xml_dict.get('size')) == 1:
        size_fix(xml_dict)
    
    xml_dict['index'] = 0
    xml_dict['url'] = ''
    xml_dict['subtype'] = ''
    
    if xml_dict.get('languages') is None:
        xml_dict['languages'] = ''
    
    return xml_dict

#%%

localMonsters = []
tob = '../open5e/legacy-source-content/monsters/tome-of-beasts/'
sources = [
   		r'../5e-database/5e-SRD-Monsters-volo.json',
   		r'../5e-database/5e-SRD-Monsters.json',
   	]
sources += [os.path.join(dp, f) for dp, dn, filenames in os.walk(tob) for f in filenames if os.path.splitext(f)[1] == '.rst' and 'index' not in f]
for f in sources:
    with codecs.open(f, 'r', encoding='utf8') as mfile:
        if f.endswith('json'):
            localMonsters += json.load(mfile)
        if f.endswith('rst'):
            localMonsters += [loadFromRst(mfile)]
            
#%%
#%%

p = Path('../fc5_xml/')
comp_dict = {x.name: str(x.resolve()) for x in p.glob('*.xml')}


for filename,comp in comp_dict.items():


    f = open(comp,'rb').read()
   
    root = etree.XML(f)
    
    
    localMonstersConverted = []
    
    for mon_xml in root.xpath('//monster'):
        monster = converter(mon_xml)
        mon_json_converted = monster_dict_refmt(monster)
        
        localMonstersConverted.append(mon_json_converted)
        
    with open(f"../fc5_xml/{os.path.splitext(filename)[0]}.json",'w') as j:
        j.write(json.dumps(localMonstersConverted))
        j.close()
#%%
    localMonstersConverted = []
    for mon_json in localMonsters:
        
        root = etree.XML(f)
        
        #some monsters have a single quote in the name text
        if "'" in mon_json['name']:
            xpath_search = ' and '.join([f"contains(text(),'{x}')" for x in mon_json['name'].split("'")])
            mon_xml = root.xpath(f"//monster/name[{xpath_search}]/ancestor::monster")
        else:
            mon_xml = root.xpath(f"//monster/name[text()='{mon_json['name']}']/ancestor::monster")
            
        if len(mon_xml) == 0:
            print(f"Didn't find any monsters for {mon_json['name']}")
            if mon_json['name'][-1] == 's':
                print('Trying again, removing the "s" on the end')
                mon_xml = root.xpath(f"//monster/name[text()='{mon_json['name'][:-1]}']/ancestor::monster")
                if len(mon_xml) == 0:
                    print('No dice. Skipping')
                    continue
            elif 'ea' in mon_json['name']:
                print("Maybe it should be 'ae' instead of 'ea' - trying that")
                mon_xml = root.xpath(f"//monster/name[text()='{mon_json['name'].replace('ea','ae')}']/ancestor::monster")
                if len(mon_xml) == 0:
                    print('No dice. Skipping')
                    continue
            elif 'Warior' in mon_json['name']:
                print('Probably because Warrior is spelled wrong.')
                mon_json['name'] = mon_json['name'].replace('Warior','Warrior')
                mon_xml = root.xpath(f"//monster/name[text()='{mon_json['name']}']/ancestor::monster")
            elif any([x[0].lower() == x[0] for x in mon_json['name'].split(' ') if x != 'of']):
                print("Some parts aren't capitalized.")
                mon_json['name'] = ' '.join([x[0].upper()+x[1:] if x != 'of' else x for x in mon_json['name'].split(' ')])
                mon_xml = root.xpath(f"//monster/name[text()='{mon_json['name']}']/ancestor::monster")
            else:
                print("Searching using contains()")
                mon_xml = root.xpath(f"//monster/name[contains(text(),'{mon_json['name']}')]/ancestor::monster")
                if len(mon_xml) == 0 and len(mon_json['name'].split(' '))>1:
                    print("Didn't work. Searching each word in the name individually")
                    xpath_search = ' and '.join([f"contains(text(),'{x}')" for x in mon_json['name'].split(' ')])
                    mon_xml = root.xpath(f"//monster/name[{xpath_search}]/ancestor::monster")
                    if len(mon_xml) == 0 and 'Of' in xpath_search:
                        xpath_search = xpath_search.replace('Of','of')
                        mon_xml = root.xpath(f"//monster/name[{xpath_search}]/ancestor::monster")
                
        mon_xml = mon_xml[0]
        
        monster = converter(mon_xml)
        mon_json_converted = monster_dict_refmt(monster)
        
        
        
        
        localMonstersConverted.append(mon_json_converted)
    
    
    with open(f"../fc5_xml/{os.path.splitext(filename)[0]}.json",'w') as j:
        j.write(json.dumps(localMonstersConverted))
        j.close()
#%%
prettify(monster)
             
#%%
for x in localMonsters:
    if  'Gazer' in x['name']:
        break
#%%
mon_json = localMonsters[70]

#%%
os.listdir(r'..\fc5_xml\*.xml')

#%%




#%%
root = etree.XML(f)
monster_xml = converter(root.xpath(f'''//monster/name[text() = 'Gazer']/ancestor::monster''')[0])

monster = monster_dict_refmt(monster_xml)

#%%
prettify(monster_xml)
#%%
list(monster)[-3].keys()
#%%

[k for k in mon_json_converted if not k in mon_json]
#%%


#%%
#TODO: GET INT VALS FROM ABILITY SCORES


locks = root.xpath(f"//monster/name[contains(text(),'Warlock')]/ancestor::monster")

[converter(x).get('name') for x in locks]
#%%
#TODO: GET INT VAL FROM 'ac' TEXT

d = xml_dict.copy()





#%%
#TODO: SPLIT 'hp' INTO 'hitpoints' AND 'hit_dice'

#%%
#TODO: PARSE SKILL LIST FROM 'skill'



#%%

    




#%%