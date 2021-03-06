from typing import Tuple, List, Dict, Callable
from collections import Counter
from itertools import permutations

Tokens = Tuple[str]
Vocabulary = List[str]
START_TOKEN = '<start>'


def clean(text: str) -> str:
    replace_table = (
        (',', ' '),
        ('.', ' '+START_TOKEN),
        (';', ' '),
        (':', ' '),
        ('-', ' '),
        ('"', ' '),
        ("'", ' '),
        ('?', ' '+START_TOKEN),
        ('!', ' '+START_TOKEN),
    )
    result = text.lower()
    for pair in replace_table:
        result = result.replace(pair[0], pair[1])
    return result


def analyse_text(text: str) -> Tuple[Tokens, Vocabulary]:
    tokens = tuple(clean(text).split())
    vocabulary = list(set(tokens))
    return tokens, vocabulary


class Frequency_Table(Dict[Tuple[str], float]):

    def __init__(self, text: str, max_n: int=3):
        tokens, vocabulary = analyse_text(text)
        self.vocabulary = vocabulary
        self.max_n = max_n
        self.freq_cache = {}
        self.N = len(tokens)
        self.V = len(vocabulary)

        for n in range(1, max_n+1):
            for i in range(len(tokens) - n + 1):
                word_tuple = tokens[i:i+n]
                try:
                    self[word_tuple] += 1
                except KeyError:
                    self[word_tuple] = 1

    def count(self, tokens: Tuple[str]) -> int:
        try:
            return self[tokens]
        except KeyError:
            return 0

    def count_tokens_of_frequency(self, frequency: int, n: int=None) -> int:
        try:
            return self.freq_cache[(frequency, n)]
        except KeyError:
            if n is None:
                n = self.max_n

            count = 0
            for key in self:
                if len(key) == n and self[key] == frequency:
                    print('found:', key)
                    count += 1

            self.freq_cache[(frequency, n)] = count
            return count

    def subdict_key_starting_with(self, tokens: Tokens) -> Dict:
        result = {}
        l = len(tokens)
        for key in self:
            if key[:l] == tokens:
                result[key] = self[key]
        return result

    def count_token_tuple_of_size(self, n: int) -> int:
        return len([key for key in self.keys() if len(key) == n])


class ML_Language_Model(object):

    def __init__(self, text: str, n: int=3):
        self.frequency_table = Frequency_Table(text, n)
        self.n = n

    def calc_final_cond_prob(self, tokens: Tokens, conditioning_tokens: Tokens) -> float:
        assert len(tokens) == 1

        ft = self.frequency_table
        cond_tokens_markov = conditioning_tokens[-self.n+1:]  # Markov property
        return ft.count(cond_tokens_markov + tokens) / ft.count(cond_tokens_markov)

    def calc_prob_by_deunion(self, tokens: Tokens, conditioning_tokens: Tokens) -> float:
        # Use chain rule of conditional probabilty to reduce length of tokens,
        # i.e. reduce the size of union of events:
        # P(cde|Sab) = P(cd|Sab) * P(e|Sabcd)
        prior_prob = self.predict(tokens[:-1], conditioning_tokens)
        if prior_prob == 0:  # Lazy evaluation to shortcircuit operation below
            prob = 0
        else:
            conditional_prob = self.predict(tokens[-1:], conditioning_tokens + tokens[:-1])
            prob = prior_prob * conditional_prob
        return prob

    def predict(self, tokens: Tokens, conditioning_tokens: Tokens = ()) -> float:

        if tokens == (START_TOKEN,):
            # All sentences should start with `<start>`
            assert len(conditioning_tokens) == 0
            prob = 1

        elif len(tokens) == 1:
            prob = self.calc_final_cond_prob(tokens, conditioning_tokens)
            # print('calculating', 'P(', ','.join(tokens), '|', ','.join(conditioning_tokens), ')')
            # print('p =', p)
        else:
            prob = self.calc_prob_by_deunion(tokens, conditioning_tokens)

        return prob


class Language_Model_Stupid_Backoff(ML_Language_Model):

    def calc_final_cond_prob(self, tokens: Tokens, conditioning_tokens: Tokens) -> float:
        assert len(tokens) == 1

        BACKOFF_VALUE = 0.4

        ft = self.frequency_table
        cond_tokens_markov = conditioning_tokens[-self.n+1:]

        sentence_count = ft.count(cond_tokens_markov + tokens)
        condition_count = ft.count(cond_tokens_markov)

        # Backoff
        backoff_times = 0
        while sentence_count == 0 or condition_count == 0:

            if not cond_tokens_markov:
                # No more conditions for backoff, use unigram
                return (BACKOFF_VALUE ** backoff_times) * (sentence_count / ft.N)

            cond_tokens_markov = cond_tokens_markov[1:]
            sentence_count = ft.count(cond_tokens_markov + tokens)
            condition_count = ft.count(cond_tokens_markov)
            backoff_times += 1

        p = sentence_count / condition_count
        return (BACKOFF_VALUE ** backoff_times) * p


class Language_Model_Additive_Smoothing(ML_Language_Model):

    def __init__(self, text: str, n: int=3, delta: int=1):
        self.frequency_table = Frequency_Table(text, n)
        self.n = n
        self.delta = delta

    def calc_final_cond_prob(self, tokens: Tokens, conditioning_tokens: Tokens) -> float:
        assert len(tokens) == 1

        ft = self.frequency_table
        cond_tokens_markov = conditioning_tokens[-self.n+1:]  # Markov property

        sentence_count = ft.count(cond_tokens_markov + tokens)
        condition_count = ft.count(cond_tokens_markov)

        sentence_count_smooth = sentence_count + self.delta
        condition_count_smooth = condition_count + \
            self.delta * (self.frequency_table.count_token_tuple_of_size(len(cond_tokens_markov)))

        # print('P(', ','.join(tokens), '|', ','.join(conditioning_tokens), ')')    
        # print(sentence_count, '/', condition_count, '->', sentence_count_smooth, '/', condition_count_smooth)

        return sentence_count_smooth / condition_count_smooth


if __name__ == '__main__':
    # text = open('data/lincoln.txt').read() + open('data/churchill.txt').read()
    text = open('data/mini.txt').read()
    # lm = Language_Model_Stupid_Backoff(text, 3)
    lm = Language_Model_Additive_Smoothing(text)
    # print(lm.predict(('<start>', 'a', 'right', 'president', 'britain')))
    # print(lm.predict(('c', 'd'), (START_TOKEN, 'a', 'b')))
    print(lm.predict(('<start>', 'a', 'XXX', 'corpus', 'is')))
    # print(lm.predict((START_TOKEN, 'a', 'b', 'c', 'd', 'e')))
    # print(lm.predict(('<start>', 'this', 'is', 'the', 'war', 'of', 'the')))
