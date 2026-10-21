"""One-off data pass from the audit: merge additional question phrasings into the knowledge files.
Idempotent: only adds phrasings that are not already present. Run from backend/: python -m scripts.expand_alts"""
from __future__ import annotations

import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "knowledge"

EN = {
    "nin-what-is": ["What is NIMC responsible for?", "What does NIN stand for?", "Why is NIN important?", "What is the national identification number used for?", "Meaning of NIN", "Tell me about NIN", "Wetin be NIN?", "What is a NIN number?"],
    "nin-eligibility": ["Who can get a NIN?", "Can my child get a NIN?", "Can a 5 year old get a NIN?", "Is there a minimum age for NIN enrolment?", "Can foreigners get a NIN?", "Are children eligible for NIN?", "Can a baby be enrolled for NIN?", "Who is eligible for NIN?"],
    "nin-enrol-steps": ["How do I get a NIN for the first time?", "How can I obtain my NIN?", "I don't have a NIN yet, how do I start?", "Where do I go to enrol for NIN?", "NIN registration steps", "How to do NIN registration", "How do I get one?", "Where can I register for NIN near me?", "Abeg how I go take get NIN?", "I want to enrol for NIN"],
    "nin-documents": ["Which ID can I use for NIN enrolment?", "Do I need a birth certificate to register for NIN?", "What should I bring to the NIMC enrolment centre?", "Is a voter's card acceptable for NIN registration?", "What do I need to carry to the NIMC office?", "Acceptable documents for NIN", "Supporting document for NIN enrolment", "Which documents are required for NIN registration?"],
    "nin-cost": ["How much is NIN?", "NIN registration fee", "NIN enrolment cost", "Why is the agent charging me for NIN?", "Do they collect money for NIN?", "Is NIN registration free of charge?", "Dem dey collect money for NIN?", "Is there a fee for NIN enrolment?", "VIP NIN enrolment fee"],
    "nin-retrieve": ["How do I check my NIN?", "How can I get my NIN on my phone?", "What code do I dial to see my NIN?", "NIN retrieval USSD", "How do I find my NIN number?", "I forgot my NIN, how do I check it?", "How to see my NIN with my phone", "Check NIN through phone"],
    "nin-slip": ["How do I print my NIN slip?", "I lost my NIN slip", "How much is NIN slip reprint?", "Where can I get the improved NIN slip?", "Reissue NIN slip", "Get NIN slip", "Download NIN slip"],
    "nin-modify-how": ["NIN modification process", "How can I change my NIN phone number?", "Where do I update my NIN address?", "Can I modify my NIN online?", "How to edit NIN details", "How do I correct my name on NIN?", "How do I change my date of birth on NIN?", "NIN self-service modification steps", "How to update NIN information"],
    "nin-modify-fees": ["How much is NIN modification?", "Cost of changing date of birth on NIN", "NIN name change fee", "How much to update my NIN phone number?", "NIN correction price", "How much is NIN DOB correction?", "How much does it cost to change my NIN details?", "Fee for NIN address update"],
    "nin-modify-docs": ["Documents required for NIN name correction", "What do I need to update my address on NIN?", "Do I need an affidavit to change my name on NIN?", "What documents do I need for NIN modification?", "Requirements to change NIN phone number", "Documents to correct NIN date of birth"],
    "nin-uses": ["Where is NIN required?", "Do I need NIN to open a bank account?", "Is NIN needed for JAMB?", "Why must I link NIN to my SIM?", "What services require NIN?", "What can I use my NIN for?", "Is NIN compulsory for passport?"],
    "nin-ninauth": ["What is NINAuth?", "What is the NIMC app called?", "How do I use the NIMC mobile app?", "Can I see my NIN in an app?", "NIMC digital ID app", "NINAuth app download"],
    "nin-scam-warning": ["Someone said they can fast track my NIN if I pay", "Is it safe to pay an agent for NIN?", "NIN fraud warning", "Should I give my NIN to an agent?", "Can an agent speed up my NIN?", "Fake NIN agents"],
    "pp-types": ["What types of passport does Nigeria issue?", "Difference between 32 and 64 page passport", "Who gets an official passport?", "Passport booklet types", "Green passport vs blue passport", "Which passport booklet should I choose?"],
    "pp-fees": ["How much is a Nigerian passport?", "Passport price in Nigeria", "Cost of 64 page passport 10 years", "How much is passport renewal?", "How much do Nigerians abroad pay for passport?", "What is the new passport fee?", "Passport fee 2025", "How much be passport now?", "Current price of international passport", "How much is a 32 page passport?", "Passport renewal cost"],
    "pp-fresh-steps": ["How do I apply for a passport?", "First time passport application Nigeria", "I want to get a passport, where do I start?", "How to apply for passport online", "Steps to get international passport", "How do I get a passport for the first time?", "Passport application steps", "New passport application"],
    "pp-documents": ["What documents are needed for passport?", "Passport requirements Nigeria", "Do I need a guarantor for passport?", "Is NIN required for passport?", "What should I bring to the passport office?", "Documents to bring for passport capture", "Which documents do I need to apply for a passport?", "Passport application requirements for adults"],
    "pp-minor": ["Passport for a minor in Nigeria", "Can my 10 year old get a passport?", "Documents for children's passport", "How do I get a passport for my baby?", "Child passport requirements", "Passport for my son or daughter", "What about a passport for my child?"],
    "pp-renewal": ["Passport renewal process", "Can I renew my passport online?", "My passport expires in 4 months, can I travel?", "How do I renew my Nigerian passport?", "Passport expired, what do I do?", "How to renew my passport", "My passport don expire"],
    "pp-change-data": ["How do I change my name on my passport after marriage?", "Correct date of birth on passport", "Passport change of data", "How to fix a spelling error on my passport", "Change of name on passport", "Passport name correction", "Correct error on passport"],
    "pp-processing-time": ["How long does passport take?", "When will my passport be ready?", "How do I track my passport application?", "Passport processing time Nigeria", "How long will it take to get my passport?", "How long passport dey take?", "Track passport status"],
    "pp-where": ["Where is the passport office?", "Can I apply for passport in Lagos if I am from Kano?", "Passport office near me", "How do I contact immigration about my passport?", "Which passport office can I use?", "Immigration office location", "Passport office in my state"],
    "pp-touts": ["Should I use an agent for passport?", "Passport fast track agent", "Is it ok to pay someone to get my passport quickly?", "Can someone help me get passport faster for a fee?", "Passport agent fee", "Avoid passport touts"],
    "dl-overview": ["Who issues driver's licence in Nigeria?", "What is the national driver's licence?", "What are driver's licence classes?", "Is FRSC in charge of driving licence?", "Which agency gives driver's licence?", "Na FRSC dey give driver licence?"],
    "dl-fresh-steps": ["How do I get a driver's licence?", "Steps to apply for driving licence", "Driver's licence application process", "I just finished driving school, what next?", "How to get drivers license in Nigeria", "New driver's licence application", "First time driver's licence", "How do I apply for a fresh driver's licence?"],
    "dl-requirements": ["What are the requirements for driver's licence?", "Minimum age for driver's licence in Nigeria", "Do I need NIN for driver's licence?", "Do I need driving school for a licence?", "Driving licence requirements", "How old must I be to get a driver's licence?", "What do I need to get a driver's licence?"],
    "dl-fees": ["How much is driver's licence?", "Driver's licence fee 5 years", "Cost of motorcycle licence", "Driver's licence price 3 years", "How much is drivers license now?", "How much dem dey charge for drivers licence?", "Driving licence cost", "How much will the licence cost?"],
    "dl-renewal": ["How do I renew my driver's licence?", "Driver's licence renewal", "My driving licence expired", "Renew driving licence online", "Driver's licence renewal steps", "Licence expired, what next?", "Drivers licence renewal process"],
    "dl-reissue": ["I lost my driver's licence", "My licence was stolen", "Replace damaged driver's licence", "Driver's licence re-issue", "I don lose my driver licence", "Lost driving licence replacement", "Stolen driver's licence what to do"],
    "dl-validity": ["How long is driver's licence valid?", "Driver's licence validity period", "Is driving licence 3 or 5 years?", "How long does a driver's licence last?", "Validity of national driver's licence", "How long is it valid?"],
    "dl-tracking": ["How do I check my driver's licence status?", "Where do I collect my driver's licence card?", "My driver's licence is not ready", "Track driver's licence application", "Where do I pick up my licence?", "Driver's licence collection", "Check licence application status"],
    "dl-commercial": ["How do I get a commercial driver's licence?", "Licence for driving trucks", "Diplomatic driver's licence", "Commercial driving licence requirements", "Licence for buses and trucks", "Commercial licence class"],
    "br-overview": ["Who issues birth certificates in Nigeria?", "What is civil registration?", "What is NPC?", "Which agency registers births?", "Who is responsible for birth registration?", "National Population Commission role", "What does NPC do?"],
    "br-how-register": ["How do I register my child's birth?", "How to get birth certificate", "Where do I register a newborn?", "Birth registration process", "How do I get my baby's birth certificate?", "Where I fit register my pikin birth?", "Birth certificate for my child", "Steps to register a birth"],
    "br-documents": ["What documents do I need to register a birth?", "Birth registration requirements", "What do I bring for birth certificate?", "Documents for birth registration", "What do I need to get a birth certificate?"],
    "br-cost": ["How much is birth certificate?", "Is birth registration free?", "Birth certificate fee NPC", "Do I pay to register my child's birth?", "Birth certificate na free?", "Cost of registering a birth", "Is it free to register a newborn?", "Birth registration charges"],
    "br-late": ["Can I get a birth certificate at 25?", "Late birth registration", "I was never registered at birth", "Birth certificate for adults", "How do I get a birth certificate as an adult?", "Registering a birth years later", "Birth certificate for a 10 year old"],
    "br-attestation-vs-certificate": ["What is attestation of birth?", "Difference between birth certificate and attestation", "Do I need attestation or birth certificate for passport?", "Attestation of birth meaning", "Birth attestation vs birth certificate"],
    "br-online-portals": ["Can I register a birth online?", "NPC online portal", "What is eCRVS?", "VitalReg", "How do I get a birth certificate online?", "Online birth registration Nigeria", "NPC self-service portal", "Can I do it online?", "E dey possible to do birth registration for internet?"],
    "br-death": ["How do I get a death certificate?", "Register a death in Nigeria", "Death registration NPC", "Where do I register my father's death?", "Death certificate requirements", "How to register a death", "Who issues death certificates?"],
    "gen-what-can-you-do": ["Good morning", "Good afternoon", "Good evening", "What can you do?", "Help", "What services do you cover?", "Hey", "Who are you?", "What is this?", "How can you help me?"],
    "gen-boundary": ["Can you apply for my passport?", "Can you check my NIN status?", "Can you book an appointment for me?", "Do you process applications?", "Can you register me for NIN?", "Are you a government website?", "Can you verify my NIN?", "Can you look up my passport status?", "My NIN is this, is it valid?"],
}

HA = {
    "nin-what-is": ["Me ake nufi da NIN?", "Me ya sa NIN yake da muhimmanci?", "Menene aikin NIMC?", "Bayani game da NIN", "Menene lambar NIN?"],
    "nin-eligibility": ["Wa zai iya samun NIN?", "Yaro zai iya samun NIN?", "Baƙo zai iya yin rajistar NIN?", "Wane shekaru ake buƙata don NIN?"],
    "nin-enrol-steps": ["Ina zan je don yin NIN?", "Yadda ake samun NIN", "Matakan yin rajistar NIN", "Ba ni da NIN, ta yaya zan fara?", "Yadda ake yin NIN a karon farko", "Ina so in yi rajistar NIN"],
    "nin-documents": ["Wace takarda zan kawo don rajistar NIN?", "Ana buƙatar takardar haihuwa don NIN?", "Abubuwan da ake buƙata don NIN", "Me zan kawo cibiyar NIMC?", "Takardun da ake karɓa don rajistar NIN", "Katin zaɓe ya isa don NIN?"],
    "nin-cost": ["Nawa ne kuɗin NIN?", "Ana biyan kuɗi don rajistar NIN?", "Kuɗin yin NIN nawa ne?", "Me ya sa wakili yake karɓar kuɗi don NIN?", "Rajistar NIN kyauta ce?", "Ana karɓar kuɗi don NIN?"],
    "nin-retrieve": ["Ta yaya zan duba NIN ɗina?", "Wane lamba zan kira don ganin NIN?", "Yadda ake samun NIN ta waya", "Yadda zan gano lambar NIN ɗina", "Na manta NIN ɗina, yaya zan duba?"],
    "nin-slip": ["Ta yaya zan buga takardar NIN?", "Nawa ne kuɗin sake buga takardar NIN?", "Yadda ake samun takardar NIN", "Sake fitar da takardar NIN"],
    "nin-modify-how": ["Ta yaya zan gyara sunana a NIN?", "Yadda ake canza lambar waya a NIN", "Zan iya gyara NIN a yanar gizo?", "Ina zan gyara adireshina a NIN?", "Hanyar gyaran NIN", "Yadda ake gyara bayanan NIN", "Ta yaya zan canza ranar haihuwa a NIN?"],
    "nin-modify-fees": ["Nawa ne kuɗin gyaran NIN?", "Kuɗin gyara ranar haihuwa a NIN", "Nawa ake biya don canza suna a NIN?", "Kuɗin canza lambar waya a NIN", "Farashin gyaran NIN", "Nawa ne gyaran NIN?"],
    "nin-modify-docs": ["Takardun gyaran suna a NIN", "Wadanne takardu nake buƙata don gyara ranar haihuwa a NIN?", "Me nake buƙata don canza adireshi a NIN?", "Takardun da ake buƙata don gyaran NIN"],
    "nin-uses": ["A ina ake buƙatar NIN?", "Ina buƙatar NIN don buɗe asusun banki?", "Me ya sa dole in haɗa NIN da layina?", "Ana buƙatar NIN don JAMB?", "Wadanne ayyuka ke buƙatar NIN?"],
    "nin-ninauth": ["Menene NINAuth?", "Menene manhajar NIMC?", "Manhajar NIN ta waya", "Yadda ake amfani da manhajar NIMC"],
    "nin-scam-warning": ["Wani ya ce zai gaggauta NIN ɗina idan na biya", "Lafiya ne in biya wakili don NIN?", "Wakilan NIN na bogi", "Zan ba wakili NIN ɗina?"],
    "pp-types": ["Wadanne nau'ikan fasfo ne ake da su?", "Bambancin fasfo mai shafi 32 da 64", "Wa ke samun fasfo na hukuma?", "Nau'in littafin fasfo"],
    "pp-fees": ["Farashin fasfo a Najeriya", "Nawa ne fasfo mai shafi 64?", "Kuɗin sabunta fasfo nawa ne?", "Nawa ne kuɗin fasfo yanzu?", "Sabon kuɗin fasfo", "Nawa ne fasfo mai shafi 32?", "Nawa ake biya don fasfo?"],
    "pp-fresh-steps": ["Yadda ake neman fasfo a karon farko", "Ina so in yi fasfo, ta ina zan fara?", "Matakan samun fasfo", "Yadda ake neman fasfo a yanar gizo", "Hanyar neman sabon fasfo"],
    "pp-documents": ["Ana buƙatar NIN don fasfo?", "Me zan kawo ofishin fasfo?", "Ana buƙatar mai lamuni don fasfo?", "Takardun da ake buƙata don neman fasfo", "Abubuwan da ake buƙata don fasfo"],
    "pp-minor": ["Fasfon yaro", "Takardun fasfon yara", "Jariri zai iya samun fasfo?", "Yadda ake samo wa yaro fasfo", "Fasfo ga ɗana ko 'yata", "Fasfon yaro ɗan shekara 10"],
    "pp-renewal": ["Yadda ake sabunta fasfo", "Fasfona ya ƙare, me zan yi?", "Zan iya sabunta fasfo a yanar gizo?", "Sabunta fasfo", "Hanyar sabunta fasfo"],
    "pp-change-data": ["Gyara kuskure a fasfo", "Canza ranar haihuwa a fasfo", "Yadda ake canza suna a fasfo", "Gyaran bayanai a fasfo"],
    "pp-processing-time": ["Yaushe fasfona zai shirya?", "Yadda ake bibiyar fasfo", "Kwana nawa ake ɗauka kafin fasfo ya fito?", "Bibiyar matsayin fasfo"],
    "pp-where": ["Zan iya neman fasfo a Legas duk da ni ɗan Kano ne?", "Ofishin shige da fice kusa da ni", "Ina ofishin fasfo yake?", "Wane ofishin fasfo zan yi amfani da shi?", "Lambar waya ta hukumar shige da fice"],
    "pp-touts": ["Lafiya ne in biya wani ya samo mini fasfo da sauri?", "Wakilin fasfo", "Yan tsakiya na fasfo", "Gaggauta fasfo ta wakili"],
    "dl-overview": ["Menene lasisin tuƙi na ƙasa?", "Ajin lasisin tuƙi", "Wace hukuma ke ba da lasisin tuƙi?", "FRSC ce ke ba da lasisin tuƙi?"],
    "dl-fresh-steps": ["Yadda ake neman lasisin tuƙi", "Na gama makarantar tuƙi, me zan yi?", "Matakan neman lasisin tuƙi", "Hanyar samun sabon lasisin tuƙi", "Neman lasisin tuƙi a karon farko", "Ta yaya zan samu lasisin tuƙi?"],
    "dl-requirements": ["Shekaru nawa ake buƙata don lasisin tuƙi?", "Ana buƙatar makarantar tuƙi don lasisi?", "Ana buƙatar NIN don lasisin tuƙi?", "Me nake buƙata don lasisin tuƙi?", "Abubuwan da ake buƙata don lasisin tuƙi"],
    "dl-fees": ["Kuɗin lasisin babur", "Nawa ne lasisin shekaru biyar?", "Farashin lasisin tuƙi", "Nawa ne kuɗin lasisin tuƙi yanzu?", "Nawa ake biya don lasisin tuƙi?", "Kuɗin lasisi na shekaru 3"],
    "dl-renewal": ["Lasisin tuƙina ya ƙare, me zan yi?", "Sabunta lasisin tuƙi", "Yadda ake sabunta lasisin tuƙi", "Hanyar sabunta lasisi"],
    "dl-reissue": ["An sace lasisina", "Lasisin tuƙina ya lalace, me zan yi?", "Lasisin tuƙi ya ɓace", "Maye gurbin lasisin da ya ɓace", "An sace lasisin tuƙina"],
    "dl-validity": ["Lasisi na shekaru 3 ko 5?", "Tsawon lokaci nawa lasisin tuƙi ke aiki?", "Ingancin lasisin tuƙi", "Shekaru nawa lasisin tuƙi ke ɗauka?"],
    "dl-tracking": ["Ina zan karɓi katin lasisina?", "Lasisina bai shirya ba", "Yadda ake duba matsayin lasisin tuƙi", "Karɓar katin lasisin tuƙi", "Bibiyar lasisin tuƙi"],
    "dl-commercial": ["Lasisin manyan motoci", "Lasisin tuƙi na jakadanci", "Lasisin tuƙi na kasuwanci", "Lasisin bas da manyan motoci", "Abubuwan da ake buƙata don lasisin kasuwanci"],
    "br-overview": ["Wa ke ba da takardar haihuwa a Najeriya?", "Menene NPC?", "Menene rajistar al'umma?", "Wace hukuma ke yin rajistar haihuwa?", "Aikin Hukumar Ƙidaya ta Ƙasa"],
    "br-how-register": ["Yadda ake samun takardar haihuwa", "Ina zan yi rajistar jariri?", "Hanyar samun takardar shaidar haihuwa", "Yadda ake yin rajistar haihuwa", "Takardar haihuwa ga jariri", "Ina zan yi rajistar haihuwar yaro?"],
    "br-documents": ["Me zan kawo don takardar haihuwa?", "Abubuwan da ake buƙata don rajistar haihuwa", "Takardun rajistar haihuwa", "Me nake buƙata don samun takardar haihuwa?"],
    "br-cost": ["Rajistar haihuwa kyauta ce?", "Ana biya don rajistar haihuwar yaro?", "Nawa ne kuɗin takardar haihuwa?", "Kuɗin rajistar haihuwa", "Ana karɓar kuɗi don takardar haihuwa?"],
    "br-late": ["Zan iya samun takardar haihuwa ina da shekara 25?", "Rajistar haihuwa a makare", "Takardar haihuwa ga babba", "Ba a yi mini rajista a haihuwa ba, me zan yi?", "Rajistar haihuwa bayan shekaru"],
    "br-attestation-vs-certificate": ["Menene takardar tabbatar da haihuwa?", "Bambanci tsakanin takardar haihuwa da tabbatarwa", "Tabbatarwa ko takardar haihuwa don fasfo?"],
    "br-online-portals": ["Shafin NPC na intanet", "Menene eCRVS?", "Zan iya yin rajistar haihuwa a yanar gizo?", "Rajistar haihuwa ta intanet", "Shafin NPC na yanar gizo", "Yadda ake samun takardar haihuwa a yanar gizo"],
    "br-death": ["Ina zan yi rajistar mutuwar mahaifina?", "Rajistar mutuwa a Najeriya", "Yadda ake samun takardar mutuwa", "Takardar shaidar mutuwa", "Wa ke ba da takardar mutuwa?"],
    "gen-what-can-you-do": ["Ina wuni", "Me za ka iya yi?", "Taimako", "Wadanne ayyuka kake rufewa?", "Wane ne kai?", "Ina kwana", "Barka da yamma", "Barka da safiya"],
    "gen-boundary": ["Za ka iya duba NIN ɗina?", "Kana sarrafa buƙatu?", "Za ka iya yi mini rajistar NIN?", "Za ka iya ɗauko mini ranar ganawa?", "Za ka iya tabbatar da NIN ɗina?", "Kai shafin gwamnati ne?"],
}

YO_NEW = [
    ("nin-documents", "nimc-nin-overview", "Àwọn ìwé tí a nílò", "Àwọn ìwé wo ni mo nílò fún ìforúkọsílẹ̀ NIN?",
     ["Kini mo nilo fun iforukosile NIN?", "Àwọn ìwé wo ni mo nílò fún NIN?", "Ṣé mo nílò ìwé-ẹ̀rí ìbí fún NIN?", "Kí ni kí n mú lọ sí ilé-iṣẹ́ NIMC?"],
     "O nílò ìwé KAN ṣoṣo tí a tẹ́wọ́gbà fún ìforúkọsílẹ̀ NIN. Àwọn ìwé tí a tẹ́wọ́gbà ni: ìwé-ẹ̀rí ìbí tàbí ìkéde ọjọ́-orí; káàdì ìdìbò (ìgbà díẹ̀ tàbí títí láé); pásípọ̀ọ̀tù Nàìjíríà; ìwé-àṣẹ awakọ̀; ìwé-ẹ̀rí ìpínlẹ̀ (certificate of origin); lẹ́tà ìjẹ́rìí láti ọ̀dọ̀ ọba ìbílẹ̀ tàbí olórí ẹ̀sìn tí a mọ̀; káàdì òṣìṣẹ́ ìjọba tàbí ilé-iṣẹ́ tí a forúkọ sílẹ̀; káàdì ilé-ẹ̀kọ́; ìwé-ẹ̀rí owó-orí; káàdì NHIS; tàbí ìwé ìṣíkiri tó wúlò fún àwọn àjèjì tó ń gbé ní Nàìjíríà lọ́nà òfin. Mú ìwé gidi lọ sí ilé-iṣẹ́ ìforúkọsílẹ̀."),
    ("nin-retrieve", "nimc-self-service", "Gbígbà NIN rẹ padà", "Báwo ni mo ṣe lè wo tàbí gba NIN mi padà?",
     ["Mo gbàgbé NIN mi", "Báwo ni mo ṣe lè wo NIN mi lórí fóònù?", "Kí ni kóòdù láti rí NIN mi?", "Bawo ni mo se le ri NIN mi?"],
     "Láti gba NIN rẹ padà, tẹ *346# láti nọ́mbà fóònù tí o lò nígbà ìforúkọsílẹ̀, yan 'NIN Retrieval' kí o sì tẹ̀lé ìtọ́ni; NIN rẹ yóò hàn lórí ìbòjú. Ilé-iṣẹ́ fóònù máa ń gba owó káàdì díẹ̀ (bíi ₦20) fún èyí. O tún lè rí NIN rẹ nínú ohun èlò NINAuth lẹ́yìn tí o bá jẹ́rìí sí ẹni tí o jẹ́. Tí nọ́mbà fóònù tí o forúkọ sílẹ̀ bá ti sọnù, o ní láti kọ́kọ́ ṣe àtúnṣe nọ́mbà fóònù rẹ nípasẹ̀ ètò ìṣàtúnṣe ara-ẹni NIMC."),
    ("nin-modify-fees", "nimc-fee-schedule-2025", "Owó àtúnṣe", "Èló ni owó àtúnṣe àlàyé NIN mi?",
     ["Èló ni owó àtúnṣe NIN?", "Elo ni lati yi ọjọ ibi pada lori NIN?", "Èló ni láti yí orúkọ padà lórí NIN?", "Owó àtúnṣe nọ́mbà fóònù NIN"],
     "Gẹ́gẹ́ bí ìwé-owó NIMC tí a tẹ̀ jáde ní oṣù May 2025: àtúnṣe ọjọ́-ìbí jẹ́ ₦28,574; ìyípadà orúkọ, àdírẹ́sì, nọ́mbà fóònù tàbí àlàyé mìíràn jẹ́ ₦2,000 fún ìbéèrè kọ̀ọ̀kan; àtúntẹ̀ ìwé NIN déédéé jẹ́ ₦600. Fún àwọn ọmọ Nàìjíríà ní òkè-òkun, àtúnṣe ọjọ́-ìbí jẹ́ $55 (Áfíríkà) tàbí $60 (níta Áfíríkà), àwọn àtúnṣe mìíràn jẹ́ $10. A ń san owó lórí ayélujára nípasẹ̀ ojú-òpó ìṣàtúnṣe ara-ẹni nìkan; iye tí ó hàn lórí ojú-òpó ìjọba nígbà ìsanwó ni ó wúlò."),
    ("pp-minor", "nis-passports", "Pásípọ̀ọ̀tù fún àwọn ọmọdé", "Báwo ni mo ṣe lè gba pásípọ̀ọ̀tù fún ọmọ mi?",
     ["Pasipootu fun omo kekere", "Àwọn ìwé fún pásípọ̀ọ̀tù ọmọdé", "Ṣé ọmọ ọdún 10 lè gba pásípọ̀ọ̀tù?", "Pásípọ̀ọ̀tù fún ọmọ ọwọ́"],
     "Fún ọmọdé (tí kò tíì pé ọdún 18): kún ìbéèrè lórí ayélujára; gbé ìwé-ẹ̀rí ìbí NPC ọmọ náà sókè; pèsè ẹ̀rí pé àwọn òbí jẹ́ ọmọ Nàìjíríà (bíi ojú-ewé àlàyé pásípọ̀ọ̀tù òbí); lẹ́tà ìgbàláàyè láti ọ̀dọ̀ òbí; fọ́tò ọmọ náà kan tí òbí tó fọwọ́ sí i buwọ́ lù; àti ìwé ìjẹ́rìí àti ẹ̀rí ìsanwó. Ọmọ náà gbọ́dọ̀ wá sí ọ́fíìsì pásípọ̀ọ̀tù pẹ̀lú òbí fún gbígbà ìka àti fọ́tò. Àwọn ọmọ tí a gbà ṣọmọ tún nílò àṣẹ ilé-ẹjọ́ àti ìfọwọ́sí Ilé-iṣẹ́ Ìjọba Ìpínlẹ̀ fún Ọ̀ràn Obìnrin."),
    ("pp-renewal", "nis-passports", "Àtúnṣe pásípọ̀ọ̀tù", "Báwo ni mo ṣe lè tún pásípọ̀ọ̀tù mi ṣe?",
     ["Pásípọ̀ọ̀tù mi ti pari, kí ni kí n ṣe?", "Pasipootu mi ti pari", "Ìlànà àtúnṣe pásípọ̀ọ̀tù", "Ṣé mo lè tún pásípọ̀ọ̀tù mi ṣe lórí ayélujára?"],
     "Àtúnṣe pásípọ̀ọ̀tù ń tẹ̀lé ìlànà kan náà pẹ̀lú ìbéèrè tuntun lórí ayélujára: 1) Béèrè ní passport.immigration.gov.ng, yan àtúnṣe, kí o sì gbé ìwé-ẹ̀rí ìbí tàbí ìkéde ọjọ́-orí, lẹ́tà ìpínlẹ̀ àti ojú-ewé àlàyé pásípọ̀ọ̀tù rẹ lọ́wọ́lọ́wọ́ sókè. 2) Sanwó lórí ayélujára kí o sì yan ọjọ́ ìpàdé. 3) Mú ìwé pásípọ̀ọ̀tù àtijọ́ lọ sí ọ́fíìsì pásípọ̀ọ̀tù ní ọjọ́ ìpàdé fún fọ́tò àti gbígbà ìka. Àkíyèsí: a ń ka pásípọ̀ọ̀tù sí èyí tó ti parí fún ìrìn-àjò tí ó bá ku oṣù mẹ́fà, nítorí náà tún un ṣe ní kùtùkùtù. Owó náà jẹ́ bákan náà pẹ̀lú ìwé tuntun."),
    ("dl-reissue", "frsc-dl-faq", "Ìwé-àṣẹ tó sọnù tàbí tí a jí", "Kí ni kí n ṣe tí ìwé-àṣẹ awakọ̀ mi bá sọnù tàbí tí a bá jí i?",
     ["Ìwé-àṣẹ awakọ̀ mi ti sọnù", "Mo pàdánù lásìnsì awakọ̀ mi", "A jí ìwé-àṣẹ awakọ̀ mi", "Lasinsi awako mi ti sonu"],
     "Tí ìwé-àṣẹ náà bá ṣì wúlò, lọ sí 'DL Application' > 'Re-Issue of Driver's Licence' ní nigeriadriverslicence.frsc.gov.ng, tẹ nọ́mbà ìwé-àṣẹ rẹ, sanwó kí o sì lọ sí ilé-iṣẹ́ gbígbà ìka. Ìròyìn ọlọ́pàá dára fún ìwé-àṣẹ tí a jí. Tí ìwé-àṣẹ tó sọnù bá ti parí, lo àṣàyàn Renewal dípò rẹ̀. Ìgbésókè (fífi kíláàsì kun tàbí yíyọ kúrò) ni a tún ń ṣe nípasẹ̀ ìlànà àtúnṣe tàbí àtúnfún pẹ̀lú nọ́mbà ìwé-àṣẹ rẹ; fífi kíláàsì kun ni a ń gba owó rẹ̀ lọ́tọ̀."),
    ("dl-renewal", "frsc-dl-faq", "Àtúnṣe", "Báwo ni mo ṣe lè tún ìwé-àṣẹ awakọ̀ mi ṣe?",
     ["Lasinsi awako mi ti pari", "Ìwé-àṣẹ awakọ̀ mi ti parí", "Àtúnṣe ìwé-àṣẹ awakọ̀", "Bawo ni mo se le tun lasinsi awako mi se?"],
     "Lọ sí nigeriadriverslicence.frsc.gov.ng, ṣí 'DL Application' kí o yan 'Renewal of Driver's Licence'. Tẹ nọ́mbà ìwé-àṣẹ rẹ lọ́wọ́lọ́wọ́, jẹ́rìí sí àlàyé rẹ, yan ọdún 3 tàbí 5 kí o sì sanwó lórí ayélujára. Lẹ́yìn náà lọ sí ilé-iṣẹ́ gbígbà ìka fún gbígbà ìka tuntun (kò sí ìdánilẹ́kọ̀ọ́ ilé-ẹ̀kọ́ awakọ̀ tuntun). Tí ìwé-àṣẹ rẹ bá ti parí o gbọ́dọ̀ lo Renewal; tí ó bá ṣì wúlò ṣùgbọ́n tó sọnù tàbí bàjẹ́, lo Re-Issue. Ìwé-àṣẹ tí a tún ṣe wúlò títí di ọjọ́ ìparí tuntun rẹ̀."),
    ("br-death", "npc-civil-registration", "Ìforúkọsílẹ̀ ikú", "Báwo ni mo ṣe lè forúkọ ikú sílẹ̀ kí n sì gba ìwé-ẹ̀rí ikú?",
     ["Iwe eri iku", "Ìwé-ẹ̀rí ikú ní Nàìjíríà", "Níbo ni mo ti lè forúkọ ikú bàbá mi sílẹ̀?", "Bawo ni a se n gba iwe eri iku?"],
     "A ń forúkọ ikú sílẹ̀ ní Àjọ Olùgbé Orílẹ̀-èdè (NPC). Mú ìwé-ẹ̀rí ìṣègùn nípa ohun tó fa ikú láti ilé-ìwòsàn (tàbí ọ̀rọ̀ ẹlẹ́rìí fún ikú ní ilé) àti ìdánimọ̀ olóògbé lọ sí ilé-iṣẹ́ ìforúkọsílẹ̀ NPC tó sún mọ́ ọ, tàbí lo iṣẹ́ ìforúkọsílẹ̀ ikú lórí ojú-òpó NPC, níbi tí a ti ń fún ní ìwé-ẹ̀rí lọ́nà dìjítà níbi tó bá yẹ. A nílò ìwé-ẹ̀rí ikú fún ìyọ̀ǹda ìsìnkú, ogún, ìdánilójú àti ẹ̀tọ́ owó-ìfẹ̀yìntì."),
    ("gen-boundary", "about-assistant", "Ààlà", "Ṣé o lè béèrè fún pásípọ̀ọ̀tù tàbí NIN fún mi?",
     ["Ṣé o lè ṣàyẹ̀wò ipò NIN mi?", "Se o le ba mi forukọ silẹ?", "Ṣé ojú-òpó ìjọba ni ọ́?", "Ṣé o ń ṣe ìbéèrè?"],
     "Rárá. Tambaya NG jẹ́ olùrànlọ́wọ́ ìwífún àti ìtọ́sọ́nà, kì í ṣe ojú-òpó ìjọba. Kò ṣe ìṣòwò, kò wọ inú àkójọ ìjọba kankan, kò jẹ́rìí sí ẹni, kò san owó tàbí fọwọ́ sí ìbéèrè, kò sì béèrè NIN rẹ, nọ́mbà pásípọ̀ọ̀tù tàbí àlàyé ara-ẹni mìíràn láé. Fún ìbéèrè tàbí ìṣòwò gidi, lo ojú-òpó ìjọba: nimc.gov.ng àti *346# fún NIN, passport.immigration.gov.ng fún pásípọ̀ọ̀tù, nigeriadriverslicence.frsc.gov.ng fún ìwé-àṣẹ awakọ̀, àti àwọn ilé-iṣẹ́ NPC tàbí ojú-òpó eCRVS fún ìforúkọsílẹ̀ ìbí."),
]

IG_NEW = [
    ("nin-documents", "nimc-nin-overview", "Akwụkwọ achọrọ", "Akwụkwọ ole ka m chọrọ maka ndebanye aha NIN?",
     ["Gịnị ka m ga-eweta maka ndebanye aha NIN?", "Akwụkwọ ole ka m chọrọ maka NIN?", "Achọrọ m akwụkwọ ọmụmụ maka NIN?", "Ihe achọrọ maka NIN"],
     "Ị chọrọ naanị OTU akwụkwọ a nabatara maka ndebanye aha NIN. Akwụkwọ a na-anabata gụnyere: akwụkwọ ọmụmụ ma ọ bụ nkwupụta afọ; kaadị ntuli aka (nwa oge ma ọ bụ nke na-adịgide); paspọtụ Naịjirịa; ikike ịnya ụgbọala; asambodo mmalite (certificate of origin); akwụkwọ ozi nkwenye site n'aka eze ọdịnala ma ọ bụ onye ndu okpukpe a maara; kaadị ọrụ gọọmentị ma ọ bụ ụlọọrụ e debanyere aha; kaadị ụlọakwụkwọ; asambodo ụtụ isi; kaadị NHIS; ma ọ bụ akwụkwọ mbata na ọpụpụ dị irè maka ndị mba ọzọ bi n'ụzọ iwu kwadoro. Weta akwụkwọ mbụ n'ụlọọrụ ndebanye aha."),
    ("nin-retrieve", "nimc-self-service", "Inwetaghachi NIN gị", "Kedu ka m ga-esi lelee ma ọ bụ nwetaghachi NIN m?",
     ["Echefuru m NIN m", "Kedu ka m ga-esi lelee NIN m na ekwentị?", "Kedu koodu m ga-akpọ ịhụ NIN m?", "Kedu ka m ga-esi chọta NIN m?"],
     "Iji nwetaghachi NIN gị, kpọọ *346# site na nọmba ekwentị i ji debanye aha, họrọ 'NIN Retrieval' ma soro ntụziaka; a ga-egosi NIN gị na ihuenyo. Ụlọọrụ ekwentị na-ana obere ego kaadị (ihe dị ka ₦20) maka nke a. Ị nwekwara ike ịhụ NIN gị na ngwa NINAuth mgbe i kwenyesịrị onwe gị. Ọ bụrụ na nọmba ekwentị i debanyere aha furu efu, ị ga-ebu ụzọ gbanwee nọmba ekwentị gị site n'usoro mgbanwe onwe nke NIMC."),
    ("nin-modify-fees", "nimc-fee-schedule-2025", "Ụgwọ mgbanwe", "Ego ole ka ịgbanwe nkọwa NIN m na-efu?",
     ["Ego ole ka mgbanwe NIN na-efu?", "Ego ole ka ịgbanwe ụbọchị ọmụmụ na NIN?", "Ego ole ka ịgbanwe aha na NIN bụ?", "Ụgwọ mgbanwe nọmba ekwentị NIN"],
     "Dị ka ndepụta ụgwọ NIMC e bipụtara na Mee 2025: mgbanwe ụbọchị ọmụmụ bụ ₦28,574; mgbanwe aha, adreesị, nọmba ekwentị ma ọ bụ data ọzọ bụ ₦2,000 kwa arịrịọ; ibipụtaghachi akwụkwọ NIN nkịtị bụ ₦600. Maka ndị Naịjirịa nọ na mba ọzọ, mgbanwe ụbọchị ọmụmụ bụ $55 (Afrịka) ma ọ bụ $60 (na mpụga Afrịka), mgbanwe ndị ọzọ bụ $10. A na-akwụ ụgwọ n'ịntanetị site na weebụsaịtị mgbanwe onwe naanị; ego e gosiri na weebụsaịtị gọọmentị n'oge ịkwụ ụgwọ bụ nke dị irè."),
    ("pp-minor", "nis-passports", "Paspọtụ maka ụmụaka", "Kedu ka m ga-esi nweta paspọtụ maka nwa m?",
     ["Paspọtụ maka nwata", "Akwụkwọ maka paspọtụ nwata", "Nwa afọ 10 ọ nwere ike inweta paspọtụ?", "Paspọtụ nwa ọhụrụ"],
     "Maka nwata (na-erubeghị afọ 18): dejupụta arịrịọ n'ịntanetị; bulite akwụkwọ ọmụmụ NPC nke nwa ahụ; nye ihe akaebe na ndị mụrụ ya bụ ụmụ amaala Naịjirịa (dị ka peeji data paspọtụ nne ma ọ bụ nna); akwụkwọ ozi nkwenye site n'aka nne ma ọ bụ nna; otu foto nwa ahụ nke nne ma ọ bụ nna kwenyere bịanyere aka; na akwụkwọ nkwenye na ihe akaebe ịkwụ ụgwọ. Nwa ahụ ga-abịa n'ụlọọrụ paspọtụ ya na nne ma ọ bụ nna maka iwere mkpịsị aka na foto. Ụmụaka e kuchiri chọkwara iwu ụlọikpe na nkwado Ụlọọrụ Steeti maka Ihe gbasara Ụmụ Nwanyị."),
    ("pp-renewal", "nis-passports", "Mmegharị", "Kedu ka m ga-esi megharịa paspọtụ m?",
     ["Paspọtụ m agwụla, gịnị ka m ga-eme?", "Paspotu m agwula", "Usoro mmegharị paspọtụ", "Enwere m ike imegharị paspọtụ m n'ịntanetị?"],
     "Mmegharị na-agbaso otu usoro ahụ dị ka arịrịọ ọhụrụ n'ịntanetị: 1) Rịọ na passport.immigration.gov.ng, họrọ mmegharị, ma bulite akwụkwọ ọmụmụ gị ma ọ bụ nkwupụta afọ, akwụkwọ ozi steeti na peeji data nke paspọtụ gị ugbu a. 2) Kwụọ ụgwọ n'ịntanetị ma họrọ ụbọchị nzukọ. 3) Weta akwụkwọ paspọtụ ochie n'ụlọọrụ paspọtụ n'ụbọchị nzukọ gị maka foto na iwere mkpịsị aka. Rịba ama: a na-ewere paspọtụ dị ka nke gwụrụ maka njem ma ọ bụrụ na ọ fọdụrụ ihe na-erughị ọnwa isii, ya mere megharịa ya n'oge. Ụgwọ bụ otu na nke akwụkwọ ọhụrụ."),
    ("dl-reissue", "frsc-dl-faq", "Ikike furu efu ma ọ bụ e zuru", "Gịnị ka m ga-eme ma ọ bụrụ na ikike ịnya ụgbọala m furu efu ma ọ bụ e zuru ya?",
     ["Ikike ịnya ụgbọala m furu efu", "E zuru laisensị m", "Laisensị ịnya ụgbọala m furu", "Ikike m mebiri emebi"],
     "Ọ bụrụ na ikike ahụ ka dị irè, gaa na 'DL Application' > 'Re-Issue of Driver's Licence' na nigeriadriverslicence.frsc.gov.ng, tinye nọmba ikike gị, kwụọ ụgwọ ma gaa n'ụlọọrụ iwere mkpịsị aka. A na-atụ aro akụkọ ndị uwe ojii maka ikike e zuru. Ọ bụrụ na ikike furu efu agwụlarị, jiri nhọrọ Renewal kama. Nkwalite (ịgbakwunye ma ọ bụ iwepụ klaasị) ka a na-emekwa site n'usoro mmegharị ma ọ bụ nnyeghachi site na nọmba ikike gị; ịgbakwunye klaasị ka a na-akwụ ụgwọ iche."),
    ("dl-renewal", "frsc-dl-faq", "Mmegharị", "Kedu ka m ga-esi megharịa ikike ịnya ụgbọala m?",
     ["Ikike ịnya ụgbọala m agwụla", "Laisensị m agwụla", "Mmegharị ikike ịnya ụgbọala", "Kedu ka m ga-esi megharịa laisensị m?"],
     "Gaa na nigeriadriverslicence.frsc.gov.ng, mepee 'DL Application' ma họrọ 'Renewal of Driver's Licence'. Tinye nọmba ikike gị ugbu a, kwenye nkọwa gị, họrọ afọ 3 ma ọ bụ 5 ma kwụọ ụgwọ n'ịntanetị. Mgbe ahụ gaa n'ụlọọrụ iwere mkpịsị aka maka iwere mkpịsị aka ọhụrụ (achọghị ọzụzụ ụlọakwụkwọ ịnya ụgbọala ọhụrụ). Ọ bụrụ na ikike gị agwụla ị ga-eji Renewal; ọ bụrụ na ọ ka dị irè mana furu efu ma ọ bụ mebie, jiri Re-Issue. Ikike e megharịrị na-adị irè ruo ụbọchị ngwụcha ọhụrụ ya."),
    ("br-death", "npc-civil-registration", "Ndebanye aha ọnwụ", "Kedu ka m ga-esi debanye aha ọnwụ ma nweta akwụkwọ ọnwụ?",
     ["Ndebanye aha ọnwụ", "Akwụkwọ ọnwụ na Naịjirịa", "Ebee ka m ga-edebanye aha ọnwụ nna m?", "Kedu ka e si enweta akwụkwọ ọnwụ?"],
     "A na-edebanye aha ọnwụ na Kọmishọn Ọnụọgụ Ndị Mmadụ Mba (NPC). Were akwụkwọ ahụike nke ihe kpatara ọnwụ site n'ụlọọgwụ (ma ọ bụ nkwupụta onye akaebe maka ọnwụ n'ụlọ) na njirimara onye nwụrụ anwụ gaa n'ụlọọrụ ndebanye aha NPC kacha nso, ma ọ bụ jiri ọrụ ndebanye aha ọnwụ na weebụsaịtị NPC, ebe a na-enye akwụkwọ ahụ na dijitalụ ebe o kwesịrị. A chọrọ akwụkwọ ọnwụ maka ikike olili, ihe nketa, mkpuchi na ụgwọ ezumike nka."),
    ("gen-boundary", "about-assistant", "Oke", "Ị nwere ike ịrịọ paspọtụ ma ọ bụ NIN n'aha m?",
     ["Ị nwere ike ilele ọnọdụ NIN m?", "Ị nwere ike idebanye m aha?", "Ị bụ weebụsaịtị gọọmentị?", "Ị na-ahazi arịrịọ?"],
     "Mba. Tambaya NG bụ onye enyemaka ozi na nduzi, ọ bụghị weebụsaịtị gọọmentị. Ọ naghị eme azụmahịa, ọ naghị abanye na nchekwa data gọọmentị ọ bụla, ọ naghị ekwenye njirimara, ọ naghị akwụ ụgwọ ma ọ bụ kwado arịrịọ, ọ dịghịkwa mgbe ọ na-arịọ NIN gị, nọmba paspọtụ ma ọ bụ njirimara onwe ọzọ. Maka arịrịọ ma ọ bụ azụmahịa ọ bụla n'ezie, jiri ụzọ gọọmentị: nimc.gov.ng na *346# maka NIN, passport.immigration.gov.ng maka paspọtụ, nigeriadriverslicence.frsc.gov.ng maka ikike ịnya ụgbọala, na ụlọọrụ ndebanye aha NPC ma ọ bụ weebụsaịtị eCRVS maka ndebanye aha ọmụmụ."),
]


def merge_alts(path: Path, extra: dict[str, list[str]]) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    added = 0
    by_id = {e["id"]: e for e in data}
    for key, alts in extra.items():
        e = by_id.get(key)
        if not e:
            print(f"  (skip) {key} not in {path.name}")
            continue
        have = {a.lower() for a in e.get("alt_questions", [])} | {e["question_text"].lower()}
        for a in alts:
            if a.lower() not in have:
                e.setdefault("alt_questions", []).append(a)
                have.add(a.lower())
                added += 1
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return added


def add_entries(path: Path, new: list) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    ids = {e["id"] for e in data}
    added = 0
    for key, doc, section, q, alts, answer in new:
        if key in ids:
            continue
        data.append({"id": key, "document": doc, "section_title": section, "question_text": q, "alt_questions": alts, "answer_text": answer})
        added += 1
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return added


if __name__ == "__main__":
    print("en alts added:", merge_alts(DATA / "entries.en.json", EN))
    print("ha alts added:", merge_alts(DATA / "entries.ha.json", HA))
    print("yo entries added:", add_entries(DATA / "entries.yo.json", YO_NEW))
    print("ig entries added:", add_entries(DATA / "entries.ig.json", IG_NEW))
