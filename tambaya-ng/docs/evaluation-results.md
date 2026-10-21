# Evaluation results (automated gold set)

Embedder: `local-hashed-ngram-v1` | Generation: extractive (offline mode) | Questions: 42 (36 in scope, 6 out of scope)

| Metric | Value |
|---|---|
| Retrieval relevance hit@1 | 100.0% |
| Retrieval relevance hit@3 | 100.0% |
| Source accuracy (top cited source is the expected entry) | 100.0% |
| In-scope questions answered (not fallback) | 100.0% |
| Fallback precision on out-of-scope questions | 100.0% |
| Language detection accuracy | 97.6% |
| Answer language accuracy | 100.0% |
| Mean total latency | 14 ms |
| p95 total latency | 15 ms |

## hit@1 by language

| Language | hit@1 |
|---|---|
| en | 100.0% |
| ha | 100.0% |
| yo | 100.0% |
| ig | 100.0% |

## Per question

| Question | Lang | Expected | Top result | Detected | Mode | ms |
|---|---|---|---|---|---|---|
| What documents do I need to enrol for a NIN? | en | nin-documents | nin-documents | en | extractive | 100 |
| Is NIN registration free? | en | nin-cost | nin-cost | en | extractive | 12 |
| I forgot my NIN, how do I check it? | en | nin-retrieve | nin-retrieve | en | extractive | 12 |
| How much is NIN date of birth correction? | en | nin-modify-fees | nin-modify-fees | en | extractive | 13 |
| Can an agent get my NIN faster if I pay? | en | nin-scam-warning | nin-scam-warning | en | extractive | 13 |
| How much does a Nigerian passport cost? | en | pp-fees | pp-fees | en | extractive | 13 |
| How do I apply for a passport for the first time? | en | pp-fresh-steps | pp-fresh-steps | en | extractive | 12 |
| What do I need to get a passport for my child? | en | pp-minor | pp-minor | en | extractive | 13 |
| How long does it take to get a passport? | en | pp-processing-time | pp-processing-time | en | extractive | 12 |
| My passport has expired, how do I renew it? | en | pp-renewal | pp-renewal | en | extractive | 12 |
| How much is a driver's licence for 5 years? | en | dl-fees | dl-fees | en | extractive | 13 |
| What are the requirements for a driver's licence? | en | dl-requirements | dl-requirements | en | extractive | 11 |
| I lost my driving licence, what do I do? | en | dl-reissue | dl-reissue | en | extractive | 12 |
| How do I renew my driver's licence? | en | dl-renewal | dl-renewal | en | extractive | 10 |
| How do I get a commercial driver's licence? | en | dl-commercial | dl-commercial | en | extractive | 11 |
| How do I register my baby's birth? | en | br-how-register | br-how-register | en | extractive | 11 |
| Is birth registration free? | en | br-cost | br-cost | en | extractive | 9 |
| I am an adult and was never registered at birth, what can I do? | en | br-late | br-late | en | extractive | 13 |
| Can I register a birth online? | en | br-online-portals | br-online-portals | en | extractive | 10 |
| How do I get a death certificate? | en | br-death | br-death | en | extractive | 10 |
| Wadanne takardu nake buƙata don rajistar NIN? | ha | nin-documents | nin-documents | ha | extractive | 15 |
| Rajistar NIN kyauta ce? | ha | nin-cost | nin-cost | ha | extractive | 12 |
| Nawa ne kuɗin fasfo? | ha | pp-fees | pp-fees | ha | extractive | 17 |
| Ta yaya zan sabunta fasfona? | ha | pp-renewal | pp-renewal | ha | extractive | 12 |
| Nawa ne kuɗin lasisin tuƙi? | ha | dl-fees | dl-fees | ha | extractive | 12 |
| Lasisin tuƙina ya ɓace, me zan yi? | ha | dl-reissue | dl-reissue | ha | extractive | 14 |
| Ta yaya zan yi rajistar haihuwar ɗana? | ha | br-how-register | br-how-register | ha | extractive | 14 |
| Rajistar haihuwa kyauta ce? | ha | br-cost | br-cost | ha | extractive | 12 |
| Ta yaya zan gyara ranar haihuwa a NIN? | ha | nin-modify-how | nin-modify-how | ha | extractive | 23 |
| Ina zan iya neman fasfo? | ha | pp-where | pp-where | ha | extractive | 13 |
| Èló ni pásípọ̀ọ̀tù? | yo | pp-fees | pp-fees | yo | extractive | 11 |
| Báwo ni mo ṣe lè forúkọ sílẹ̀ fún NIN? | yo | nin-enrol-steps | nin-enrol-steps | yo | extractive | 13 |
| Èló ni ìwé-àṣẹ awakọ̀? | yo | dl-fees | dl-fees | yo | extractive | 12 |
| Ego ole ka paspọtụ na-efu? | ig | pp-fees | pp-fees | ig | extractive | 12 |
| Kedu ka m ga-esi debanye aha ọmụmụ nwa m? | ig | br-how-register | br-how-register | ig | extractive | 12 |
| Kedu ka m ga-esi nweta NIN? | ig | nin-enrol-steps | nin-enrol-steps | ig | extractive | 11 |
| What is the weather in Lagos today? | en | out of scope | fallback | en | fallback | 9 |
| Who won the Premier League? | en | out of scope | fallback | en | fallback | 8 |
| How do I cook jollof rice? | en | out of scope | fallback | en | fallback | 8 |
| How do I get a Canadian visa? | en | out of scope | fallback | en | fallback | 10 |
| Yaya yanayin Kano yau? | ha | out of scope | fallback | ha | fallback | 13 |
| Tell me a joke | en | out of scope | fallback | yo | fallback | 8 |