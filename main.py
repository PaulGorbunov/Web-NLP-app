import numpy as np
import re
import pickle
import os
import nltk
from nltk.corpus import wordnet
from gensim.models import KeyedVectors
from functools import *
from multiprocessing import Pool

model =(KeyedVectors.load_word2vec_format("data/GoogleNews-vectors-negative300.bin",binary=True,limit = 200000),KeyedVectors.load_word2vec_format("data/ruscorpora_mean_hs.model.bin", binary=True,limit = 200000))

f_names = ["data/tags/","data/brief/","data/content/"]
preority = [2,1.5,1]
min_score = 400

def tag(word):
    word = word.lower()
    try :
        if len(wordnet.synsets(word))!=0 :
            return (0,word)
    except LookupError:
        nltk.download('wordnet')
        return tag(word)
    try:
        from pymystem3 import Mystem
        m = Mystem()
        processed = m.analyze(word)[0]
        lemma = processed["analysis"][0]["lex"].lower().strip()
        pos = processed["analysis"][0]["gr"].split(',')[0]
        pos = pos.split('=')[0].strip()
        tagged = lemma+'_'+pos
        return (1,tagged)
    except IndexError:
        return (-1,)

def get_vect(word):
    try :
        w = tag(word)
        if w[0] != -1:
            return (w[0],model[w[0]][w[1]])
        return (-1,)
    except KeyError:
        return (-1,)
    
def prep_text(text):
    tx = re.findall("(?=[а-яА-Яa-zA-ZÇâêîôûàèùëïüé]{1})[а-яА-Яa-zA-ZÇâêîôûàèùëïüé-]*[а-яА-Яa-zA-ZÇâêîôûàèùëïüé]+['’]?[а-яА-Яa-zA-Z]{0,4}",text)
    for h in range(len(tx)):
        tx[h] = tx[h].lower()
    return tx
 

def sent_matr(text):
    text = prep_text(text)
    matr = [[],[]]
    p = Pool(4)
    (lambda: [matr[x[0]].append(x[1]) for x in p.map(get_vect,text) if x[0]!=-1])()
    return matr

    
def get_score(inp):
    que_m,text_m = inp
    res = 0
    for u in range(len(que_m)):
        if np.shape(que_m[u])[0] != 0 and np.shape(text_m[u])[0] != 0 :
            res += np.sum(np.dot(que_m[u],text_m[u]))
    return res 

    
def _global():
    with open("global",'rb') as f:
        r = pickle.load(f)
    return r


def _upd_global(name):
    gl = _global()
    gl["l"].append(name)
    gl["d"][name.split("_")[-1]] = name
    with open("global",'wb') as f:
        pickle.dump(gl,f)
    
def upd_global(d,l):
    info = {"d":d,"l":l}
    with open("global",'wb') as f:
        pickle.dump(info,f)
    
def get_article(que,conn):
    texts = []
    artic_lis = _global()["l"]
    for u in range(len(artic_lis)):
        for d in f_names:
            with open(d+artic_lis[u],'rb') as f:
                texts.append(pickle.load(f))
    que = sent_matr(que)
    score = [(que,texts[u]) for u in range(len(texts))]
    p = Pool(4)
    ans = p.map(get_score,score)
    cou = []
    for u in range(len(ans)//3):
        s = 0
        for h in range(3):
            s+= preority[h]*ans[u*3+h]
        cou.append(s)
    med_val = (max(cou)-min(cou))/2
    if med_val > min_score :
        cou = [(cou[u],artic_lis[u]) for u in range(len(cou)) if cou[u] >= med_val]
        cou.sort(key=lambda x:x[0])
        cou = [x[1] for x in cou]
    else:
        cou = []
    if (len(cou) != 0):
        conn.send(cou)
        conn.close()
    else:
        conn.send(0)
        conn.close()
    
    
def create_text_matrix(inf,name):
    try :
        (lambda: [os.mkdir(u[:len(u)]) for u in f_names])()
    except FileExistsError:
        pass
    tags,bri,text = inf
    lis =  [tags,prep_text(bri),prep_text(text)]
    for u in range(len(lis)):
        matr = [[],[]]
        (lambda: [matr[x[0]].append(x[1]) for x in (get_vect(w) for w in lis[u]) if x[0]!=-1])()
        for g in range(len(matr)):
            matr[g] = np.transpose(matr[g])
        with open(f_names[u]+name,'wb') as f:
            pickle.dump(matr,f)
         
         
def rem_global(_id):
    gl = _global()
    try :
        gl["l"].remove(gl["d"][_id])
        del gl["d"][_id]
        upd_global(gl["d"],gl["l"])
        return 0
    except ValueError: 
        return 1
    except KeyError:
        return 1
        

def delete_ind(ind):
    dict_names = _global()["d"]
    try:
        rem_global(ind)
        for u in f_names:
            os.remove(u+dict_names[ind])
        return 0
    except KeyError:
        return 1
    except FileNotFoundError:
        return 1


def create_global():
    if "global" in os.listdir():
        return 0
    nltk.download('wordnet')
    info = {"d":{},"l":[]}
    with open("global","wb") as f:
        pickle.dump(info,f)
    return 0
        
create_global()
