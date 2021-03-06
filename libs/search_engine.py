from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
from elasticsearch_dsl.query import Q
import nltk
import hunspell
import wordsegment as ws
from operator import itemgetter
from flask import *

spellchecker = hunspell.HunSpell('/usr/share/hunspell/en_US.dic',\
                                 '/usr/share/hunspell/en_US.aff')
ws.load()

class SearchEngine(object):
    """A class for searching movies in corpus with
    elasticsearch.
    """

    def __init__(self, client, index, doc_type):
        """Initialize metadata.
        """
        super(SearchEngine, self).__init__()
        self.client = client
        self.index = index
        self.doc_type = doc_type

    def search(self, form, start, end):
        """Process query and search relevant movies.
        """
        query = str(form.get("query"))
        term_list = query.split(' ')
        for i in xrange(len(term_list)):
            if not spellchecker.spell(term_list[i]):
                suggestions = spellchecker.suggest(term_list[i])
                if suggestions:
                    prev = ''
                    if i == 0:
                        prev = '<s>'
                    else:
                        prev = term_list[i-1]
                    candidates = [(s, ws.BIGRAMS.get((prev+' '+s), 0)) for s in suggestions]
                    winner = max(candidates, key=itemgetter(1))
                    flash(winner[0])
                else: flash("Oops! A mistake?..")
                return render_template('index.html')
        token_tags = nltk.pos_tag(nltk.word_tokenize(query))
        keywords = [token for token, tag in token_tags if \
            tag.startswith("NN") or \
            tag.startswith("VB") or \
            tag.startswith("PRP") or \
            tag.startswith("JJ") or \
            tag.startswith("RB")]
        rtmin, rtmax = form.get("rtmin"), form.get("rtmax")
        runtime = {}
        if rtmin: runtime["gte"] = int(rtmin)
        if rtmax: runtime["lte"] = int(rtmax)
        s = Search(using=self.client, index=self.index,
            doc_type=self.doc_type).query(Q("match_phrase",
            Plot={"query": ' '.join(keywords), "slop": 50})) \
            .filter("range", Runtime=runtime)
        language = form.get("language")
        if language: s = s.filter("match", Language=language)
        s = s[start:end]
        res = s.execute()
        return res

    def search_by_id(self, id):
        """Retrieve a document by id.
        """
        s = Search(using=self.client, index=self.index,
            doc_type=self.doc_type).query("term", _id=id)
        res = s.execute()
        return res[0] if res else None
