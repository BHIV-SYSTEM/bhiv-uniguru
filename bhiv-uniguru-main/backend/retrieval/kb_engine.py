from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, Optional, List


logger = logging.getLogger(__name__)

MIN_RETRIEVAL_SCORE = 10.0
NO_RELEVANT_KB_ANSWER = "I couldn't find relevant information in the knowledge base."


STOPWORDS = {
    "a", "an", "and", "any", "are", "as", "about", "be", "by", "can", "do",
    "does", "for", "from", "give", "how", "in", "is", "it", "me", "name",
    "of", "one", "or", "related", "should", "tell", "text", "the", "this",
    "to", "what", "which", "who", "why", "with", "according",
}


class SovereignRetriever:
    """
    Improved Retrieval Engine for UniGuru.

    Features:
    - keyword matching
    - title matching
    - category matching
    - query expansion
    - better scoring
    - lower false rejection
    """

    def __init__(self, index_path: Optional[str] = None):

        self.index_path = index_path or os.path.normpath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "knowledge",
                "index",
                "master_index.json"
            )
        )

        self.index: Dict[str, Any] = {}
        self.kosha_entries: List[Dict[str, Any]] = []

        self._load_index()
        self._load_kosha_entries()


    # ----------------------------
    # Load index
    # ----------------------------

    def _load_index(self):

        if not os.path.exists(self.index_path):

            logger.warning(
                "Index missing %s",
                self.index_path
            )

            self.index = {}
            return


        try:

            with open(
                self.index_path,
                "r",
                encoding="utf-8-sig"
            ) as f:

                raw = f.read()


            try:
                loaded = json.loads(raw)

            except json.JSONDecodeError:

                repaired = re.sub(
                    r"\\(?![\\\"/bfnrtu])",
                    "/",
                    raw
                )

                loaded = json.loads(repaired)


            if isinstance(loaded, dict):

                self.index = loaded

                logger.info(
                    "Index loaded. Keywords: %s",
                    len(self.index)
                )


            else:

                self.index = {}


        except Exception as e:

            logger.error(
                "Index load error %s",
                e
            )

            self.index = {}



    def _load_kosha_entries(self):
        self.kosha_entries = []
        candidate_paths = [
            os.path.join(os.path.dirname(__file__), "..", "data", "kosha", "kosha_entries.jsonl"),
            os.path.join(os.path.dirname(__file__), "..", "..", "backend", "data", "kosha", "kosha_entries.jsonl"),
        ]

        for path in candidate_paths:
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    for line in handle:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            payload = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        content = str(payload.get("clean_content") or payload.get("content") or "").strip()
                        if not content:
                            continue
                        self.kosha_entries.append(
                            {
                                "content": content,
                                "source": str(payload.get("source") or payload.get("knowledge_id") or "kosha_entry"),
                                "domain": str(payload.get("domain") or ""),
                                "metadata": {
                                    "source": str(payload.get("source") or payload.get("knowledge_id") or "kosha_entry"),
                                    "domain": str(payload.get("domain") or ""),
                                    "knowledge_id": str(payload.get("knowledge_id") or ""),
                                },
                            }
                        )
                logger.info("Loaded %s KOSHA entries from %s", len(self.kosha_entries), path)
                break
            except Exception as exc:
                logger.warning("Unable to load KOSHA entries from %s: %s", path, exc)

    # ----------------------------
    # Normalize text
    # ----------------------------

    def normalize(self,text):

        return set(
            word
            for word in re.sub(
                    r"[^\w\s]",
                    " ",
                    str(text).lower()
                ).split()
            if len(word) > 1 and word not in STOPWORDS
        )



    # ----------------------------
    # Query expansion
    # ----------------------------

    def expand_query(self,query):

        query=query.lower()

        mapping={


            "biography":[
                "life",
                "history",
                "born",
                "biography",
                "about"
            ],


            "swaminarayan":[
                "bhagwan",
                "baps",
                "akshar",
                "purushottam",
                "gunatitanand"
            ],


            "gnana":[
                "jnan",
                "gyan",
                "knowledge",
                "wisdom"
            ],


            "jnana":[
                "jnan",
                "gyan",
                "knowledge",
                "wisdom"
            ],


            "vairagya":[
                "detachment",
                "renunciation",
                "dispassion"
            ],


            "bhakti":[
                "devotion",
                "devotional",
                "worship"
            ],


            "maryada":[
                "discipline",
                "conduct",
                "restraint"
            ],


            "satsang":[
                "association",
                "company",
                "saints",
                "devotees"
            ],


            "sant":[
                "sadhu",
                "saint",
                "guru"
            ],


            "shikshapatri":[
                "code",
                "conduct",
                "duties"
            ],


            "vachanamrut":[
                "discourses",
                "teachings",
                "scripture"
            ],


            "shant":[
                "peace",
                "calm",
                "tranquil"
            ],


            "association":[
                "satpurush",
                "satsang",
                "saint",
                "guru",
                "brahmaswarup"
            ],


            "spiritually":[
                "satpurush",
                "saint",
                "akshar",
                "brahmarup"
            ],


            "elevated":[
                "satpurush",
                "saint",
                "brahmaswarup",
                "akshar"
            ],


            "self":[
                "nishkam",
                "purity",
                "celibacy",
                "discipline"
            ],


            "control":[
                "nishkam",
                "purity",
                "celibacy",
                "discipline"
            ],


            "purity":[
                "nishkam",
                "thought",
                "word",
                "deed"
            ],


            "student":[
                "shikshapatri",
                "daily",
                "duties",
                "discipline"
            ],


            "values":[
                "shikshapatri",
                "panch",
                "vartman",
                "conduct"
            ],


            "practices":[
                "prayer",
                "puja",
                "scripture",
                "ekadashi",
                "devotion"
            ],


            "devoted":[
                "bhakti",
                "devotion",
                "purushottam",
                "upasana"
            ],


            "moksha":[
                "salvation",
                "liberation"
            ]
        }


        words=list(
            self.normalize(
                query
            )
        )


        expanded=set(words)

        if "अहिंसा" in query:
            expanded.update(
                {
                    "ahimsa",
                    "nonviolence",
                    "non",
                    "violence",
                    "dharma",
                    "paramo",
                    "dharma",
                }
            )

        if "शांत" in query:
            expanded.update(
                {
                    "peace",
                    "calm",
                    "devotion",
                    "bhakti"
                }
            )

        mapping.update({
            "brahman": [
                "ultimate",
                "ultimate reality",
                "absolute reality",
                "atman",
                "paramatman",
                "supreme",
                "nirguna",
                "saguna",
            ],
            "upanishad": [
                "upanishads",
                "vedanta",
                "vedas",
                "taittiriya",
                "chashtogya",
                "ibrisha",
            ],
            "ayurveda": [
                "charaka",
                "sushruta",
                "ashtanga",
                "vedic medicine",
                "medical",
                "health",
            ],
            "purana": [
                "puranas",
                "mahabharata",
                "ramayana",
                "bhagavata",
                "skanda",
                "myth",
                "mythology",
            ],
            "dharma": [
                "duty",
                "law",
                "righteousness",
                "ethics",
                "conduct",
            ],
        })

        for word in words:

            if word in mapping:

                expanded.update(
                    mapping[word]
                )


        return " ".join(expanded)


    # ----------------------------
    # Text helpers
    # ----------------------------

    def _normalize_flat(
        self,
        text
    ):

        return re.sub(
            r"\s+",
            " ",
            re.sub(
                r"[^\w\s]",
                " ",
                str(text).lower()
            )
        ).strip()


    def _strip_frontmatter(
        self,
        text
    ):

        return re.sub(
            r"^---[\s\S]*?---\s*",
            "",
            str(text),
            flags=re.MULTILINE
        ).strip()


    def _split_paragraphs(
        self,
        text
    ):

        body=self._strip_frontmatter(
            text
        )

        paragraphs=[
            part.strip()
            for part in re.split(
                r"\n\s*\n+",
                body
            )
            if part.strip()
        ]

        seen=set()
        deduped=[]

        for paragraph in paragraphs:

            stripped=paragraph.strip()

            if stripped.startswith("#") or stripped.lower().startswith("uniguru citation"):
                continue

            normalized=self._normalize_flat(
                paragraph
            )

            if not normalized or normalized in seen:
                continue

            seen.add(
                normalized
            )
            deduped.append(
                paragraph
            )

        return deduped


    def _split_sentences(
        self,
        text
    ):

        compact=re.sub(
            r"\s+",
            " ",
            str(text).strip()
        )

        fragments=re.split(
            r"(?:\n+|(?<=[.!?।])\s+)",
            compact
        )

        sentences=[]
        seen=set()

        for fragment in fragments:

            candidate=fragment.strip(" \t-•*#0123456789.:")

            if not candidate:
                continue

            normalized=self._normalize_flat(
                candidate
            )

            if not normalized or normalized in seen:
                continue

            seen.add(
                normalized
            )
            sentences.append(
                candidate
            )

        return sentences


    def _score_text(
        self,
        query_words,
        text
    ):

        if not text:
            return 0

        text_words=self.normalize(
            text
        )

        return len(
            query_words.intersection(
                text_words
            )
        )


    def _select_supporting_paragraphs(
        self,
        query_words,
        top_matches,
        max_paragraphs=5
    ):

        selected=[]
        seen=set()

        for match in top_matches:

            entry=match.get(
                "entry",
                {}
            )

            if not isinstance(
                entry,
                dict
            ):
                entry={}

            content=str(
                entry.get(
                    "content",
                    ""
                )
            )

            paragraphs=self._split_paragraphs(
                content
            )

            if not paragraphs:
                continue

            scored=[]

            for index, paragraph in enumerate(paragraphs):

                score=self._score_text(
                    query_words,
                    paragraph
                )

                if score <= 0:
                    continue

                scored.append(
                    (
                        score,
                        -index,
                        paragraph
                    )
                )

            if scored:
                scored.sort(
                    reverse=True
                )
                limit=2 if scored[0][0] >= 2 else 1
                chosen=[
                    item[2]
                    for item in scored[:limit]
                ]
            else:
                chosen=[paragraphs[0]]

            for paragraph in chosen:

                normalized=self._normalize_flat(
                    paragraph
                )

                if not normalized or normalized in seen:
                    continue

                seen.add(
                    normalized
                )
                selected.append(
                    paragraph
                )

                if len(selected) >= max_paragraphs:
                    return selected

        return selected


    def _synthesize_answer(
        self,
        query,
        top_matches
    ):

        query_words=self.normalize(
            self.expand_query(
                query
            )
        )

        paragraphs=self._select_supporting_paragraphs(
            query_words,
            top_matches
        )

        if not paragraphs:
            return ""

        selected_sentences=[]
        seen=set()

        for paragraph in paragraphs:

            sentences=self._split_sentences(
                paragraph
            )

            if not sentences:
                sentences=[paragraph]

            scored_sentences=[]

            for index, sentence in enumerate(sentences):

                score=self._score_text(
                    query_words,
                    sentence
                )

                if score > 0:
                    scored_sentences.append(
                        (
                            score,
                            -index,
                            sentence
                        )
                    )

            if scored_sentences:
                scored_sentences.sort(
                    reverse=True
                )
                candidates=[
                    item[2]
                    for item in scored_sentences[:2]
                ]
            else:
                candidates=sentences[:1]

            for sentence in candidates:

                normalized=self._normalize_flat(
                    sentence
                )

                if not normalized or normalized in seen:
                    continue

                seen.add(
                    normalized
                )
                selected_sentences.append(
                    sentence.strip()
                )

                if len(selected_sentences) >= 6:
                    break

            if len(selected_sentences) >= 6:
                break

        if len(selected_sentences) < 3:

            for paragraph in paragraphs:

                for sentence in self._split_sentences(
                    paragraph
                ):

                    normalized=self._normalize_flat(
                        sentence
                    )

                    if not normalized or normalized in seen:
                        continue

                    seen.add(
                        normalized
                    )
                    selected_sentences.append(
                        sentence.strip()
                    )

                    if len(selected_sentences) >= 3:
                        break

                if len(selected_sentences) >= 3:
                    break

        return " ".join(
            selected_sentences[:6]
        ).strip()




    # ----------------------------
    # Score document
    # ----------------------------

    def score_document(
        self,
        query,
        keyword,
        entry
    ):


        score=0


        query_words=self.normalize(query)


        keyword_words=self.normalize(keyword)



        # keyword match

        score += len(
            query_words.intersection(
                keyword_words
            )
        ) * 3



        if isinstance(entry,dict):


            metadata=entry.get(
                "metadata",
                {}
            )


            if not isinstance(metadata,dict):

                metadata={}


            title=str(
                entry.get(
                    "title",
                    metadata.get(
                        "source",
                        ""
                    )
                )
            )


            category=str(
                entry.get(
                    "category",
                    metadata.get(
                        "category",
                        ""
                    )
                )
            )


            source=str(
                metadata.get(
                    "source",
                    ""
                )
            )


            content=str(
                entry.get(
                    "content",
                    ""
                )
            )



            # title boost

            title_words=self.normalize(title)

            score += len(
                query_words.intersection(title_words)
            ) * 5



            # category boost

            category_words=self.normalize(category)

            score += len(
                query_words.intersection(category_words)
            ) * 4


            # source filename boost

            source_words=self.normalize(source)

            score += len(
                query_words.intersection(source_words)
            ) * 4



            # content match

            content_words=self.normalize(content)

            score += len(
                query_words.intersection(content_words)
            )

            domain = str(metadata.get("domain", ""))
            domain_words = self.normalize(domain)
            score += len(query_words.intersection(domain_words)) * 2

            if re.search(r"\bi don't know\b|not explicitly|provided context does not", content, re.IGNORECASE):
                score -= 5

            lowered_content = content.lower()
            if "swaminarayan" in lowered_content or "quantum" in lowered_content:
                score -= 2

            topic_terms = ["ayurveda", "upanishad", "purana", "puranas", "brahman", "charaka", "taittiriya", "ahimsa", "dharma", "sanskrit"]
            matched_terms = [term for term in topic_terms if term in lowered_content]
            if matched_terms:
                score += 4 * len(matched_terms)

            query_terms = set(self.normalize(query))
            content_terms = set(self.normalize(content))
            overlap = len(query_terms.intersection(content_terms))
            score += overlap

            if query_terms:
                direct_topic_hits = [term for term in query_terms if term in content_terms]
                if direct_topic_hits:
                    score += 3 * len(direct_topic_hits)

            if "ayurveda" in query_words or "ayurveda" in query_terms:
                if "charaka" in lowered_content or "sushruta" in lowered_content or "ayurvedic" in lowered_content:
                    score += 6

            if any(term in lowered_content for term in ["not ayurveda", "not related to ayurveda", "not about ayurveda"]):
                score -= 8

            # If query indicates programming intent, prefer programming documents
            programming_signals = {"python", "program", "programming", "code", "coding", "developer", "algorithm", "function", "method", "script"}
            if query_words.intersection(programming_signals) or query.lower().find("programming guru") != -1:
                # boost documents that mention programming-related terms
                if "python" in lowered_content:
                    score += 10
                if any(t in lowered_content for t in ["code", "program", "function", "script", "algorithm", "github", "pip", "numpy", "pandas"]):
                    score += 6
                # penalize clearly spiritual / scripture documents to avoid misrouting
                if any(t in lowered_content for t in ["bhagavad", "gita", "upanishad", "purana", "shrimad", "vedas", "mantra"]):
                    score -= 12

        return score




    # ----------------------------
    # Main query
    # ----------------------------

    def retrieve_with_candidates(
        self,
        user_query:str,
        subject: Optional[str] = None
    ):

        expanded_query=self.expand_query(
            user_query
        )

        logger.info(
            "Original query: %s",
            user_query
        )

        logger.info(
            "Expanded query: %s",
            expanded_query
        )

        scored_entries=[]

        for keyword,entries in self.index.items():
            if not isinstance(entries,list):
                continue
            for entry in entries:
                score=self.score_document(
                    expanded_query,
                    keyword,
                    entry
                )
                if score <= 0:
                    continue
                # If a subject filter is provided and it indicates programming,
                # skip entries that do not contain programming signals to ensure
                # the UI selection returns programming concepts only.
                if subject and "program" in subject.lower():
                    lowered_content = str(entry.get("content","") or "").lower()
                    lowered_title = str(entry.get("title","") or "").lower()
                    programming_signals = ["python","javascript","code","function","algorithm","script","program","github","pip","numpy","pandas"]
                    if not any(tok in lowered_content or tok in lowered_title for tok in programming_signals):
                        continue
                scored_entries.append(
                    {
                        "keyword":keyword,
                        "entry":entry,
                        "score":score,
                    }
                )

        for entry in self.kosha_entries:
            score=self.score_document(
                expanded_query,
                str(entry.get("domain") or "kosha"),
                entry
            )
            if score <= 0:
                continue
            scored_entries.append(
                {
                    "keyword": str(entry.get("domain") or "kosha"),
                    "entry": entry,
                    "score": score,
                }
            )

        scored_entries.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        unique_entries=[]
        seen_entries=set()

        for item in scored_entries:
            entry=item.get(
                "entry",
                {}
            )

            if not isinstance(entry,dict):
                entry={}

            metadata=entry.get(
                "metadata",
                {}
            )

            if not isinstance(metadata,dict):
                metadata={}

            identity=self._normalize_flat(
                metadata.get(
                    "source",
                    ""
                )
                or entry.get(
                    "content",
                    ""
                )[:300]
            )

            if not identity or identity in seen_entries:
                continue

            seen_entries.add(
                identity
            )
            unique_entries.append(
                item
            )

        scored_entries=unique_entries

        best=scored_entries[0] if scored_entries else None
        best_score=best["score"] if best else 0

        query_terms=set(self.normalize(expanded_query))
        best_entry=best.get("entry", {}) if best else {}
        if not isinstance(best_entry, dict):
            best_entry={}
        best_text=" ".join([
            str(best_entry.get("title", "")),
            str(best_entry.get("category", "")),
            str(best_entry.get("source", "")),
            str(best_entry.get("content", "")),
        ])
        best_terms=set(self.normalize(best_text))
        direct_overlap=len(query_terms.intersection(best_terms))

        # bigram overlap (helps detect short phrase matches)
        q_tokens = self._normalize_flat(expanded_query).split()
        b_tokens = self._normalize_flat(best_text).split()
        q_bigrams = set(
            " ".join(q_tokens[i:i+2])
            for i in range(max(0, len(q_tokens)-1))
        )
        b_bigrams = set(
            " ".join(b_tokens[i:i+2])
            for i in range(max(0, len(b_tokens)-1))
        )
        bigram_overlap = len(q_bigrams.intersection(b_bigrams))

        overlap_ratio = float(direct_overlap) / max(1, len(query_terms))

        logger.info(
            "Best score: %s",
            best_score
        )
        logger.info(
            "Retrieval threshold: %s",
            MIN_RETRIEVAL_SCORE
        )
        logger.info(
            "Query terms: %s; direct overlap: %s; overlap_ratio: %.2f; bigram_overlap: %s",
            sorted(query_terms),
            direct_overlap,
            overlap_ratio,
            bigram_overlap,
        )

        def single_document_response():
            entry=best["entry"] if best else {}
            if not isinstance(entry,dict):
                entry={}
            metadata=entry.get(
                "metadata",
                {}
            )
            if not isinstance(metadata,dict):
                metadata={}
            return {
                "answer": entry.get("content", ""),
                "source_file": metadata.get("source"),
                "confidence_level": round(min(best_score/10, 1), 2) if best else 0.0,
                "verified": True,
            }

        # Require both a minimum score and a stronger signal that the
        # top document is contextually relevant. Allow matches when any
        # of these strong signals are present to avoid false negatives:
        # - at least 2 shared normalized tokens
        # - a sufficiently large overlap ratio of query tokens
        # - a shared bigram (phrase) between query and document
        # - or an elevated absolute score (very confident match)
        strong_signal = (
            direct_overlap >= 2
            or overlap_ratio >= 0.4
            or bigram_overlap >= 1
            or best_score >= (MIN_RETRIEVAL_SCORE * 1.5)
        )

        if best and best_score >= MIN_RETRIEVAL_SCORE and strong_signal:
            try:
                min_score=max(MIN_RETRIEVAL_SCORE * 0.6, 1)
                top_matches=[
                    item
                    for item in scored_entries
                    if item.get("score", 0) >= min_score
                ][:5]

                if len(top_matches) < 3:
                    top_matches=scored_entries[:min(5, len(scored_entries))]

                filtered_matches = []
                for item in top_matches:
                    entry = item.get("entry", {})
                    content = str(entry.get("content", "") or "")
                    if re.search(r"\bi don't know\b|not explicitly|provided context does not", content, re.IGNORECASE):
                        continue
                    filtered_matches.append(item)
                if filtered_matches:
                    top_matches = filtered_matches

                if not top_matches:
                    top_matches=[best]

                synthesized=self._synthesize_answer(
                    user_query,
                    top_matches
                )

                if not synthesized:
                    return single_document_response()

                top_entry=best.get("entry", {})
                if not isinstance(top_entry,dict):
                    top_entry={}
                metadata=top_entry.get("metadata", {})
                if not isinstance(metadata,dict):
                    metadata={}
                avg_score=sum(float(match.get("score", 0)) for match in top_matches) / len(top_matches)

                return {
                    "answer": synthesized,
                    "source_file": metadata.get("source"),
                    "confidence_level": round(min(avg_score/10, 1), 2),
                    "verified": True,
                    "candidates": [
                        {
                            "content": str(item.get("entry", {}).get("content", "") or "").strip(),
                            "source": str(item.get("entry", {}).get("metadata", {}).get("source") or item.get("entry", {}).get("source") or ""),
                            "score": float(item.get("score", 0) or 0.0),
                        }
                        for item in top_matches
                    ],
                }
            except Exception as e:
                logger.warning(
                    "Top-match synthesis failed, using single-document fallback: %s",
                    e
                )
                return single_document_response()

        return {
            "answer": NO_RELEVANT_KB_ANSWER,
            "source_file": None,
            "confidence_level": round(best_score / 10, 2) if best else 0.0,
            "verified": False,
        }

    def query(
        self,
        user_query:str
    ):
        return self.retrieve_with_candidates(user_query)


_engine=SovereignRetriever()


def retrieve(query:str):
    return _engine.query(query)


def retrieve_with_candidates(query:str, subject: Optional[str] = None):
    return _engine.retrieve_with_candidates(query, subject=subject)
