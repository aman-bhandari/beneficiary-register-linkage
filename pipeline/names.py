"""Name material for the synthetic population, by community.

Every name is held in Devanagari with the Roman spellings the same name is actually written with in Indian
records (Kamla/Kamala, Mohd/Md/Mohammad, Mondal/Mandal). The generator picks a spelling per register; the linkage
code never sees this table and has to reconcile spellings on its own.

Community shares per district come from Census 2011 (Scheduled Caste / Scheduled Tribe shares, and mother-tongue
shares for Udham Singh Nagar: Hindi 62%, Punjabi 10%, Bengali 7.9%, Urdu 6.4%, Kumaoni 5.2%, Tharu 2.9%).
"""

# ------------------------------------------------------------------------------------------------ Kumaoni (hills)
KUM_MALE = [
    ("रमेश", ["Ramesh"]), ("सुरेश", ["Suresh"]), ("मोहन", ["Mohan"]), ("गोविन्द", ["Govind", "Gobind", "Govinda"]),
    ("हरीश", ["Harish", "Hareesh"]), ("भूपाल", ["Bhupal", "Bhoopal"]), ("कुन्दन", ["Kundan"]),
    ("दीवान", ["Diwan", "Dewan", "Deewan"]), ("प्रकाश", ["Prakash", "Parkash"]), ("भुवन", ["Bhuwan", "Bhuvan"]),
    ("नवीन", ["Naveen", "Navin"]), ("पूरन", ["Puran", "Pooran"]), ("किशन", ["Kishan", "Kisan"]),
    ("कैलाश", ["Kailash", "Kailas"]), ("त्रिलोक", ["Trilok"]), ("गोपाल", ["Gopal"]), ("हीरा", ["Heera", "Hira"]),
    ("खीम", ["Kheem", "Khim"]), ("लक्ष्मण", ["Laxman", "Lakshman"]), ("उमेश", ["Umesh"]),
    ("जगदीश", ["Jagdish", "Jagadish"]), ("बहादुर", ["Bahadur"]), ("भगवान", ["Bhagwan", "Bhagawan"]),
    ("जीवन", ["Jeevan", "Jivan"]), ("नन्दन", ["Nandan"]), ("शंकर", ["Shankar", "Sankar"]),
    ("राजेन्द्र", ["Rajendra", "Rajender"]), ("महेन्द्र", ["Mahendra", "Mahender"]), ("दिनेश", ["Dinesh"]),
    ("मनोज", ["Manoj"]), ("पंकज", ["Pankaj"]), ("विनोद", ["Vinod", "Binod"]), ("राकेश", ["Rakesh"]),
    ("कमल", ["Kamal"]), ("सुन्दर", ["Sundar"]), ("आनन्द", ["Anand"]), ("दयाल", ["Dayal"]), ("गिरीश", ["Girish"]),
    ("ललित", ["Lalit"]), ("नरेन्द्र", ["Narendra", "Narender"]), ("भरत", ["Bharat"]), ("हरि", ["Hari"]),
    ("केशव", ["Keshav", "Keshaw"]), ("प्रताप", ["Pratap", "Partap"]), ("मदन", ["Madan"]), ("गणेश", ["Ganesh"]),
    ("चन्द्रशेखर", ["Chandrashekhar", "Chandra Shekhar", "Chander Shekhar"]), ("हेम", ["Hem"]),
    ("देवेन्द्र", ["Devendra", "Devender"]), ("बलवन्त", ["Balwant", "Balvant"]), ("धर्म", ["Dharam", "Dharm"]),
    ("उदय", ["Uday", "Udai"]), ("कृपाल", ["Kripal", "Kirpal"]), ("मोती", ["Moti"]), ("रघुवीर", ["Raghuvir", "Raghubir"]),
    ("शिव", ["Shiv", "Siv"]), ("सुरेन्द्र", ["Surendra", "Surender"]), ("नारायण", ["Narayan"]),
    ("अमित", ["Amit"]), ("रोहित", ["Rohit"]), ("विकास", ["Vikas", "Bikas"]), ("संजय", ["Sanjay"]),
    ("अंकित", ["Ankit"]), ("मनीष", ["Manish"]), ("दीपक", ["Deepak", "Dipak"]),
]
KUM_FEMALE = [
    ("कमला", ["Kamla", "Kamala"]), ("पार्वती", ["Parvati", "Parwati", "Parbati"]), ("जानकी", ["Janki", "Jaanki", "Janaki"]),
    ("बसन्ती", ["Basanti"]), ("दीपा", ["Deepa", "Dipa"]), ("हेमा", ["Hema"]), ("तुलसी", ["Tulsi"]),
    ("राधा", ["Radha"]), ("सीता", ["Sita", "Seeta"]), ("गीता", ["Geeta", "Gita"]),
    ("भगवती", ["Bhagwati", "Bhagawati", "Bhagvati"]), ("पुष्पा", ["Pushpa"]), ("मीना", ["Meena", "Mina"]),
    ("सुनीता", ["Sunita", "Suneeta"]), ("कविता", ["Kavita", "Kavitha"]), ("नीमा", ["Neema", "Nima"]),
    ("हंसी", ["Hansi"]), ("दुर्गा", ["Durga"]), ("लक्ष्मी", ["Laxmi", "Lakshmi"]), ("तारा", ["Tara"]),
    ("कौशल्या", ["Kaushalya", "Koshalya", "Kaushilya"]), ("मोहिनी", ["Mohini"]), ("बीना", ["Beena", "Bina"]),
    ("रेखा", ["Rekha"]), ("अनीता", ["Anita", "Aneeta"]), ("किरन", ["Kiran"]), ("गोविन्दी", ["Govindi", "Gobindi"]),
    ("धनुली", ["Dhanuli"]), ("खष्टी", ["Khashti", "Khasti"]), ("चम्पा", ["Champa"]), ("मालती", ["Malti", "Malati"]),
    ("शान्ति", ["Shanti", "Santi"]), ("इन्द्रा", ["Indra", "Indira"]), ("प्रेमा", ["Prema"]), ("आनन्दी", ["Anandi"]),
    ("भागीरथी", ["Bhagirathi", "Bhagirthi"]), ("उमा", ["Uma"]), ("गंगा", ["Ganga"]), ("हरुली", ["Haruli"]),
    ("पदमा", ["Padma", "Padama"]), ("नन्दी", ["Nandi"]), ("विमला", ["Vimla", "Bimla", "Vimala"]),
    ("सरस्वती", ["Saraswati", "Sarasvati"]), ("उर्मिला", ["Urmila"]), ("दीपिका", ["Deepika", "Dipika"]),
    ("पूजा", ["Pooja", "Puja"]), ("नेहा", ["Neha"]), ("प्रियंका", ["Priyanka"]), ("ज्योति", ["Jyoti"]),
    ("मंजू", ["Manju"]), ("सरिता", ["Sarita"]), ("ममता", ["Mamta", "Mamata"]),
]

# ------------------------------------------------------------------------------------ Hindi-belt plains (Hindu)
PLAINS_MALE = [
    ("रमेश", ["Ramesh"]), ("सुरेश", ["Suresh"]), ("राजेश", ["Rajesh"]), ("सुनील", ["Sunil"]), ("अनिल", ["Anil"]),
    ("मुकेश", ["Mukesh"]), ("सन्तोष", ["Santosh", "Santos"]), ("ओमप्रकाश", ["Omprakash", "Om Prakash"]),
    ("रामकिशोर", ["Ramkishor", "Ram Kishore"]), ("श्यामलाल", ["Shyamlal", "Shyam Lal"]), ("राजकुमार", ["Rajkumar", "Raj Kumar"]),
    ("प्रमोद", ["Pramod", "Parmod"]), ("विजय", ["Vijay", "Bijay"]), ("अशोक", ["Ashok", "Asok"]), ("राम", ["Ram"]),
    ("कृष्ण", ["Krishna", "Krishan", "Kishan"]), ("हरिओम", ["Hariom", "Hari Om"]), ("नरेश", ["Naresh"]),
    ("दिनेश", ["Dinesh"]), ("महेश", ["Mahesh"]), ("योगेश", ["Yogesh"]), ("रामपाल", ["Rampal", "Ram Pal"]),
    ("चन्द्रपाल", ["Chandrapal", "Chanderpal"]), ("धर्मपाल", ["Dharampal", "Dharmpal"]), ("सत्यपाल", ["Satyapal", "Satpal"]),
    ("मोहनलाल", ["Mohanlal", "Mohan Lal"]), ("रामस्वरूप", ["Ramswaroop", "Ram Swaroop", "Ramsarup"]),
    ("भगवानदास", ["Bhagwandas", "Bhagwan Das"]), ("सोनू", ["Sonu"]), ("मोनू", ["Monu"]), ("पप्पू", ["Pappu"]),
    ("राहुल", ["Rahul"]), ("अमित", ["Amit"]), ("विकास", ["Vikas"]), ("संजीव", ["Sanjeev", "Sanjiv"]),
]
PLAINS_FEMALE = [
    ("सुनीता", ["Sunita"]), ("अनीता", ["Anita"]), ("रेखा", ["Rekha"]), ("कमलेश", ["Kamlesh"]), ("सावित्री", ["Savitri", "Savitree"]),
    ("शान्ति", ["Shanti", "Santi"]), ("उर्मिला", ["Urmila"]), ("मुन्नी", ["Munni"]), ("गुड्डी", ["Guddi"]),
    ("कुसुम", ["Kusum"]), ("रामकली", ["Ramkali", "Ram Kali"]), ("फूलमती", ["Phoolmati", "Fulmati", "Phulmati"]),
    ("शीला", ["Sheela", "Shila"]), ("सरोज", ["Saroj"]), ("गीता", ["Geeta", "Gita"]), ("राजवती", ["Rajwati", "Rajvati"]),
    ("रामवती", ["Ramwati", "Ramvati"]), ("भगवती", ["Bhagwati"]), ("मीरा", ["Meera", "Mira"]), ("पुष्पा", ["Pushpa"]),
    ("विमला", ["Vimla", "Bimla"]), ("सन्तोष", ["Santosh"]), ("राजबाला", ["Rajbala", "Raj Bala"]), ("ओमवती", ["Omwati", "Omvati"]),
    ("चन्द्रकला", ["Chandrakala", "Chanderkala"]), ("पूजा", ["Pooja", "Puja"]), ("प्रीति", ["Preeti", "Priti"]),
    ("नीतू", ["Neetu", "Nitu"]), ("रीना", ["Reena", "Rina"]), ("सोनी", ["Soni"]),
]
PLAINS_HINDU_SURNAMES = [("गंगवार", ["Gangwar"]), ("यादव", ["Yadav", "Yadaw"]), ("कश्यप", ["Kashyap", "Kasyap"]),
                         ("सैनी", ["Saini", "Sainy"]), ("शर्मा", ["Sharma"]), ("गुप्ता", ["Gupta"]), ("वर्मा", ["Verma", "Varma"]),
                         ("मौर्य", ["Maurya", "Mourya"]), ("पाल", ["Pal"]), ("राठौर", ["Rathore", "Rathaur"]),
                         ("चौहान", ["Chauhan", "Chouhan"]), ("प्रजापति", ["Prajapati"]), ("कुशवाहा", ["Kushwaha", "Kushwah"]),
                         ("रस्तोगी", ["Rastogi"]), ("अग्रवाल", ["Agarwal", "Agrawal"]), ("सिंह", ["Singh"])]
PLAINS_SC_SURNAMES = [("सागर", ["Sagar"]), ("जाटव", ["Jatav", "Jatab"]), ("वाल्मीकि", ["Valmiki", "Balmiki"]),
                      ("दिवाकर", ["Diwakar", "Divakar"]), ("कुमार", ["Kumar"]), ("भारती", ["Bharti", "Bharati"]),
                      ("गौतम", ["Gautam", "Gotam"]), ("राम", ["Ram"])]

# ------------------------------------------------------------------------------------------------ Sikh (Punjabi)
SIKH_MALE = [("गुरप्रीत", ["Gurpreet", "Gurprit"]), ("हरप्रीत", ["Harpreet", "Harprit"]), ("मनप्रीत", ["Manpreet"]),
             ("जसप्रीत", ["Jaspreet"]), ("हरजिन्दर", ["Harjinder", "Harjindar"]), ("कुलदीप", ["Kuldeep", "Kuldip"]),
             ("बलविन्दर", ["Balwinder", "Balvinder"]), ("सुखविन्दर", ["Sukhwinder", "Sukhvinder"]), ("गुरमीत", ["Gurmeet", "Gurmit"]),
             ("जसवन्त", ["Jaswant", "Jasvant"]), ("करनैल", ["Karnail"]), ("दलजीत", ["Daljeet", "Daljit"]),
             ("परमजीत", ["Paramjeet", "Paramjit"]), ("अमरजीत", ["Amarjeet", "Amarjit"]), ("सुरजीत", ["Surjeet", "Surjit"]),
             ("गुरदीप", ["Gurdeep", "Gurdip"]), ("इन्द्रजीत", ["Inderjeet", "Inderjit"]), ("हरभजन", ["Harbhajan"]),
             ("बलदेव", ["Baldev"]), ("निर्मल", ["Nirmal"]), ("जगतार", ["Jagtar"]), ("सतनाम", ["Satnam"])]
SIKH_FEMALE = [("गुरप्रीत", ["Gurpreet", "Gurprit"]), ("हरप्रीत", ["Harpreet"]), ("मनप्रीत", ["Manpreet"]),
               ("जसप्रीत", ["Jaspreet"]), ("हरजीत", ["Harjeet", "Harjit"]), ("परमजीत", ["Paramjeet", "Paramjit"]),
               ("कुलवन्त", ["Kulwant", "Kulvant"]), ("सुरिन्दर", ["Surinder", "Surender"]), ("बलजीत", ["Baljeet", "Baljit"]),
               ("सुखविन्दर", ["Sukhwinder"]), ("अमरजीत", ["Amarjeet"]), ("गुरमीत", ["Gurmeet"]), ("राजविन्दर", ["Rajwinder", "Rajvinder"]),
               ("जसवीर", ["Jasveer", "Jasbir"]), ("मनजीत", ["Manjeet", "Manjit"]), ("निर्मल", ["Nirmal"])]
SIKH_SURNAMES = [("सन्धू", ["Sandhu"]), ("गिल", ["Gill"]), ("ढिल्लों", ["Dhillon", "Dhilon"]), ("रन्धावा", ["Randhawa"]),
                 ("विर्क", ["Virk"]), ("बाजवा", ["Bajwa"]), ("सिद्धू", ["Sidhu"]), ("ग्रेवाल", ["Grewal"]), ("बराड़", ["Brar", "Barar"]),
                 ("मान", ["Mann", "Maan"]), ("चीमा", ["Cheema", "Chima"]), ("औलख", ["Aulakh", "Olakh"])]

# --------------------------------------------------------------------------------------------------------- Muslim
MUSLIM_MALE = [("सलीम", ["Salim", "Saleem"]), ("आरिफ", ["Arif", "Aarif"]), ("रशीद", ["Rashid", "Rasheed"]), ("यूसुफ", ["Yusuf", "Yousuf"]),
               ("इरफान", ["Irfan"]), ("इमरान", ["Imran"]), ("शकील", ["Shakil", "Shakeel"]), ("जावेद", ["Javed", "Jawed"]),
               ("नसीम", ["Nasim", "Naseem"]), ("अकरम", ["Akram"]), ("अनवर", ["Anwar", "Anvar"]), ("इकबाल", ["Iqbal", "Ikbal"]),
               ("फारूख", ["Farooq", "Farukh", "Faruk"]), ("मुस्तकीम", ["Mustkeem", "Mustaqim"]), ("शाहिद", ["Shahid"]),
               ("वसीम", ["Wasim", "Waseem"]), ("नईम", ["Naeem", "Naim"]), ("कलीम", ["Kalim", "Kaleem"]), ("रफीक", ["Rafiq", "Rafik"]),
               ("मुन्ना", ["Munna"]), ("सद्दाम", ["Saddam"]), ("आसिफ", ["Asif", "Aasif"])]
MUSLIM_FEMALE = [("शबाना", ["Shabana"]), ("नाजमा", ["Nazma", "Najma"]), ("रेहाना", ["Rehana", "Rihana"]), ("फरजाना", ["Farzana", "Farjana"]),
                 ("सायरा", ["Saira", "Sayra"]), ("शमीम", ["Shamim", "Shameem"]), ("नसरीन", ["Nasreen", "Nasrin"]),
                 ("जरीना", ["Zarina", "Jarina"]), ("अफसाना", ["Afsana"]), ("रुखसाना", ["Rukhsana", "Ruksana"]),
                 ("सलमा", ["Salma"]), ("अमीना", ["Amina", "Ameena"]), ("हसीना", ["Hasina", "Haseena"]), ("मुमताज", ["Mumtaz"]),
                 ("गुलशन", ["Gulshan"]), ("सितारा", ["Sitara"])]
MUSLIM_SURNAMES = [("खान", ["Khan"]), ("अंसारी", ["Ansari"]), ("कुरैशी", ["Qureshi", "Kureshi", "Quraishi"]), ("सैफी", ["Saifi"]),
                   ("सिद्दीकी", ["Siddiqui", "Siddiqi", "Sidiqui"]), ("मलिक", ["Malik"]), ("हुसैन", ["Hussain", "Husain"]),
                   ("अहमद", ["Ahmad", "Ahmed"]), ("सलमानी", ["Salmani"]), ("मंसूरी", ["Mansoori", "Mansuri"])]
MUSLIM_PREFIX = ("मोहम्मद", ["Mohd", "Mohd.", "Md", "Mohammad", "Mohammed", "Muhammad", "Mo."])

# -------------------------------------------------------------------------------------------------------- Bengali
BENGALI_MALE = [("नितई", ["Nitai"]), ("गोपाल", ["Gopal"]), ("निमाई", ["Nimai"]), ("सुबोध", ["Subodh"]), ("प्रदीप", ["Pradip", "Pradeep"]),
                ("बिकाश", ["Bikash", "Bikas", "Vikash"]), ("दिलीप", ["Dilip", "Deelip"]), ("तपन", ["Tapan"]), ("स्वपन", ["Swapan", "Sapan"]),
                ("सुकुमार", ["Sukumar"]), ("निखिल", ["Nikhil"]), ("अमल", ["Amal"]), ("बिमल", ["Bimal", "Vimal"]),
                ("कार्तिक", ["Kartik", "Kartick"]), ("हरिपद", ["Haripad", "Haripada"]), ("गौर", ["Gour", "Gaur"])]
BENGALI_FEMALE = [("गीता", ["Gita", "Geeta"]), ("मीरा", ["Mira", "Meera"]), ("सन्ध्या", ["Sandhya", "Sondhya"]), ("कल्पना", ["Kalpana"]),
                  ("माया", ["Maya"]), ("अंजलि", ["Anjali"]), ("शिखा", ["Shikha", "Sikha"]), ("मिनती", ["Minati"]),
                  ("पूर्णिमा", ["Purnima", "Poornima"]), ("लक्ष्मी", ["Laxmi", "Lakshmi"]), ("सरस्वती", ["Saraswati"]),
                  ("बासन्ती", ["Basanti"]), ("छबि", ["Chhabi", "Chabi"]), ("अर्चना", ["Archana"])]
BENGALI_SURNAMES = [("दास", ["Das"]), ("मण्डल", ["Mondal", "Mandal"]), ("विश्वास", ["Biswas", "Bishwas"]), ("सरकार", ["Sarkar", "Sircar"]),
                    ("हालदार", ["Haldar", "Halder"]), ("राय", ["Roy", "Rai"]), ("मजूमदार", ["Majumdar", "Mazumdar"]),
                    ("घोष", ["Ghosh", "Ghose"]), ("पाल", ["Pal", "Paul"])]

# -------------------------------------------------------------------------------------------- Tharu and Buksa (ST)
THARU_MALE = [("रामसिंह", ["Ram Singh", "Ramsingh"]), ("भगवान", ["Bhagwan"]), ("जयपाल", ["Jaipal", "Jai Pal"]), ("मोहन", ["Mohan"]),
              ("बुद्धि", ["Buddhi", "Budhi"]), ("धनीराम", ["Dhaniram", "Dhani Ram"]), ("छोटे", ["Chhote", "Chote"]),
              ("हरपाल", ["Harpal"]), ("गेंदालाल", ["Gendalal", "Genda Lal"]), ("लालता", ["Lalta"]), ("सोहन", ["Sohan"]),
              ("बब्लू", ["Bablu", "Bubblu"]), ("राजू", ["Raju"])]
THARU_FEMALE = [("कमला", ["Kamla"]), ("रामकली", ["Ramkali"]), ("सुशीला", ["Sushila", "Susheela"]), ("मायावती", ["Mayawati", "Mayavati"]),
                ("फूलवती", ["Phoolwati", "Fulwati"]), ("चमेली", ["Chameli"]), ("लीलावती", ["Leelawati", "Lilavati"]),
                ("गुड्डी", ["Guddi"]), ("शान्ति", ["Shanti"]), ("राधा", ["Radha"])]
THARU_SURNAMES = [("राणा", ["Rana"]), ("राणा", ["Rana"]), ("बुक्सा", ["Buksa", "Boksa"]), ("सिंह", ["Singh"])]

KUM_SURNAMES = {
    "rajput": [("बिष्ट", ["Bisht", "Bist"]), ("नेगी", ["Negi"]), ("रावत", ["Rawat", "Ravat"]), ("मेहरा", ["Mehra"]),
               ("अधिकारी", ["Adhikari"]), ("बोरा", ["Bora"]), ("कार्की", ["Karki"]), ("भण्डारी", ["Bhandari"]),
               ("रौतेला", ["Rautela"]), ("मनराल", ["Manral"]), ("कनवाल", ["Kanwal"]), ("खाती", ["Khati"]),
               ("जीना", ["Jeena", "Jina"]), ("परिहार", ["Parihar"]), ("फर्त्याल", ["Phartyal", "Fartyal"]),
               ("मेहता", ["Mehta"]), ("डसीला", ["Dasila"]), ("बिष्ट", ["Bisht"]), ("रावत", ["Rawat"]), ("नेगी", ["Negi"])],
    "brahmin": [("जोशी", ["Joshi"]), ("पन्त", ["Pant", "Panth"]), ("पाण्डे", ["Pandey", "Pande", "Pandy"]),
                ("तिवारी", ["Tiwari", "Tewari"]), ("भट्ट", ["Bhatt", "Bhat"]), ("काण्डपाल", ["Kandpal"]),
                ("उप्रेती", ["Upreti"]), ("लोहनी", ["Lohani", "Lohni"]), ("पाठक", ["Pathak"]),
                ("मठपाल", ["Mathpal"]), ("उपाध्याय", ["Upadhyay", "Upadhyaya"]), ("कर्नाटक", ["Karnatak"]),
                ("जोशी", ["Joshi"]), ("पन्त", ["Pant"])],
    "sc": [("आर्या", ["Arya", "Aarya"]), ("टम्टा", ["Tamta"]), ("कोहली", ["Kohli"]), ("आर्य", ["Arya"])],
}

DEVI = ("देवी", ["Devi", "Debi"])
KAUR = ("कौर", ["Kaur", "Kour"])
RANI = ("रानी", ["Rani"])
SINGH = ("सिंह", ["Singh"])

# community -> naming convention. category: the social-category field departments record.
COMMUNITIES = {
    "kumaoni_rajput": dict(male=KUM_MALE, female=KUM_FEMALE, surnames=KUM_SURNAMES["rajput"], male_middle=[SINGH],
                           female_suffix=DEVI, category="general"),
    "kumaoni_brahmin": dict(male=KUM_MALE, female=KUM_FEMALE, surnames=KUM_SURNAMES["brahmin"],
                            male_middle=[("चन्द्र", ["Chandra", "Chander", "Chand"]), ("दत्त", ["Datt", "Dutt"])],
                            female_suffix=DEVI, category="general"),
    "kumaoni_sc": dict(male=KUM_MALE, female=KUM_FEMALE, surnames=KUM_SURNAMES["sc"],
                       male_middle=[("राम", ["Ram"]), ("लाल", ["Lal"])], female_suffix=DEVI, category="sc"),
    "plains_hindu": dict(male=PLAINS_MALE, female=PLAINS_FEMALE, surnames=PLAINS_HINDU_SURNAMES, male_middle=[],
                         female_suffix=DEVI, category="obc_general"),
    "plains_sc": dict(male=PLAINS_MALE, female=PLAINS_FEMALE, surnames=PLAINS_SC_SURNAMES, male_middle=[],
                      female_suffix=DEVI, category="sc"),
    "sikh": dict(male=SIKH_MALE, female=SIKH_FEMALE, surnames=SIKH_SURNAMES, male_middle=[SINGH], male_middle_always=True,
                 female_suffix=KAUR, female_suffix_always=True, category="general"),
    "muslim": dict(male=MUSLIM_MALE, female=MUSLIM_FEMALE, surnames=MUSLIM_SURNAMES, male_prefix=MUSLIM_PREFIX,
                   female_suffix=None, category="obc_general"),
    "bengali": dict(male=BENGALI_MALE, female=BENGALI_FEMALE, surnames=BENGALI_SURNAMES,
                    male_middle=[("चन्द्र", ["Chandra", "Chandro"])], female_suffix=RANI, category="general"),
    "tharu": dict(male=THARU_MALE, female=THARU_FEMALE, surnames=THARU_SURNAMES, male_middle=[], female_suffix=DEVI,
                  category="st"),
}

# Census 2011 shares. Almora: SC 22.68%, ST 0.21% (folded into the rest). Udham Singh Nagar: SC 14.45%, ST 7.46%,
# Punjabi 10%, Bengali 7.9%, Urdu 6.4% (Muslim share taken as 22%, which includes Hindi-speaking Muslims), Kumaoni 5.2%.
DISTRICT_COMMUNITIES = {
    "Almora": {"kumaoni_rajput": 0.52, "kumaoni_brahmin": 0.2532, "kumaoni_sc": 0.2268},
    "Udham Singh Nagar": {"plains_hindu": 0.335, "plains_sc": 0.1445, "sikh": 0.10, "muslim": 0.22, "bengali": 0.079,
                          "tharu": 0.0746, "kumaoni_rajput": 0.03, "kumaoni_brahmin": 0.0169},
}

# Muslim women are usually recorded with a second name of their own rather than a husband's surname
MUSLIM_FEMALE_SECOND = [("खातून", ["Khatoon", "Khatun"]), ("बेगम", ["Begum", "Begam"]), ("परवीन", ["Parveen", "Praveen", "Parvin"]),
                        ("बानो", ["Bano", "Banu"]), ("निशा", ["Nisha"])]
COMMUNITIES["muslim"]["female_second"] = MUSLIM_FEMALE_SECOND


# ------------------------------------------------------------------------------------------ larger name pools
def compound(prefixes, suffixes):
    """North Indian given names are often compounds: राम+लाल = Ramlal / Ram Lal. Both spellings occur in records."""
    out = []
    for pd_, pr in prefixes:
        for sd, sr in suffixes:
            out.append((pd_ + sd, [pr + sr.lower(), f"{pr} {sr}"]))
    return out


THARU_MALE += compound([("राम", "Ram"), ("श्याम", "Shyam"), ("हर", "Har"), ("जय", "Jai"), ("धनी", "Dhani"),
                        ("गेंदा", "Genda"), ("बुद्धि", "Buddhi"), ("मोहन", "Mohan"), ("सोहन", "Sohan"), ("छोटे", "Chhote"),
                        ("बाबू", "Babu"), ("मंगल", "Mangal"), ("शिव", "Shiv"), ("भगवान", "Bhagwan")],
                       [("लाल", "Lal"), ("पाल", "Pal"), ("सिंह", "Singh"), ("प्रसाद", "Prasad"), ("दास", "Das")])
THARU_FEMALE += compound([("राम", "Ram"), ("फूल", "Phool"), ("लीला", "Leela"), ("चन्द्र", "Chandra"), ("गंगा", "Ganga"),
                          ("शान्ति", "Shanti"), ("सुख", "Sukh"), ("धन", "Dhan"), ("प्रेम", "Prem"), ("राज", "Raj")],
                         [("वती", "Wati"), ("कली", "Kali"), ("मती", "Mati"), ("देई", "Dei")])
PLAINS_MALE += compound([("राम", "Ram"), ("श्याम", "Shyam"), ("हरि", "Hari"), ("शिव", "Shiv"), ("जय", "Jai"),
                         ("ओम", "Om"), ("राज", "Raj"), ("चन्द्र", "Chandra"), ("सत्य", "Satya"), ("वीर", "Veer")],
                        [("पाल", "Pal"), ("कुमार", "Kumar"), ("प्रकाश", "Prakash"), ("किशोर", "Kishore"), ("सिंह", "Singh")])
PLAINS_FEMALE += compound([("राम", "Ram"), ("राज", "Raj"), ("चन्द्र", "Chandra"), ("ओम", "Om"), ("प्रेम", "Prem"),
                           ("शशि", "Shashi"), ("सुमन", "Suman")], [("वती", "Wati"), ("बाला", "Bala"), ("लता", "Lata")])
SIKH_MALE += [("जसविन्दर", ["Jaswinder", "Jasvinder"]), ("सुखदेव", ["Sukhdev"]), ("गुरचरन", ["Gurcharan", "Gurcharn"]),
              ("हरपाल", ["Harpal"]), ("जगजीत", ["Jagjeet", "Jagjit"]), ("राजिन्दर", ["Rajinder", "Rajender"]),
              ("सरबजीत", ["Sarabjeet", "Sarabjit"]), ("तरसेम", ["Tarsem"]), ("अवतार", ["Avtar", "Autar"]),
              ("भूपिन्दर", ["Bhupinder", "Bhupender"]), ("चरनजीत", ["Charanjeet", "Charanjit"]), ("दविन्दर", ["Davinder", "Devinder"]),
              ("गुरनाम", ["Gurnam"]), ("हरदीप", ["Hardeep", "Hardip"]), ("जसबीर", ["Jasbir", "Jasveer"]),
              ("कुलविन्दर", ["Kulwinder", "Kulvinder"]), ("लखविन्दर", ["Lakhwinder"]), ("मनदीप", ["Mandeep", "Mandip"]),
              ("नवदीप", ["Navdeep"]), ("रणजीत", ["Ranjeet", "Ranjit"]), ("सुखजिन्दर", ["Sukhjinder"]), ("तेजिन्दर", ["Tejinder"]),
              ("बलजीत", ["Baljeet", "Baljit"]), ("गुरविन्दर", ["Gurwinder", "Gurvinder"]), ("हरविन्दर", ["Harwinder"])]
SIKH_FEMALE += [("जसविन्दर", ["Jaswinder"]), ("सुखजीत", ["Sukhjeet", "Sukhjit"]), ("कमलजीत", ["Kamaljeet", "Kamaljit"]),
                ("रणजीत", ["Ranjeet", "Ranjit"]), ("सिमरन", ["Simran"]), ("नवनीत", ["Navneet", "Navnit"]), ("रूपिन्दर", ["Rupinder"]),
                ("हरमीत", ["Harmeet", "Harmit"]), ("दलजीत", ["Daljeet", "Daljit"]), ("बलविन्दर", ["Balwinder"]),
                ("जसलीन", ["Jasleen"]), ("कुलदीप", ["Kuldeep"]), ("मनिन्दर", ["Maninder"]), ("सतविन्दर", ["Satwinder", "Satvinder"]),
                ("अमनदीप", ["Amandeep"]), ("रविन्दर", ["Ravinder", "Ravindar"])]
MUSLIM_MALE += [("अब्दुल", ["Abdul"]), ("इस्लाम", ["Islam"]), ("जमील", ["Jamil", "Jameel"]), ("खालिद", ["Khalid"]),
                ("मुजफ्फर", ["Muzaffar", "Mujaffar"]), ("नदीम", ["Nadeem", "Nadim"]), ("परवेज", ["Parvez", "Pervez"]),
                ("कासिम", ["Qasim", "Kasim"]), ("रहीस", ["Rahees", "Rais"]), ("साबिर", ["Sabir", "Saabir"]),
                ("तौफीक", ["Taufiq", "Toufik"]), ("उस्मान", ["Usman", "Osman"]), ("वकील", ["Wakil", "Vakil"]),
                ("जाकिर", ["Zakir", "Jakir"]), ("अजीज", ["Aziz", "Ajij"]), ("बाबू", ["Babu"]), ("दिलशाद", ["Dilshad"]),
                ("फईम", ["Faheem", "Fahim"]), ("गुलफाम", ["Gulfam"]), ("हनीफ", ["Hanif", "Haneef"]), ("इलियास", ["Ilyas", "Iliyas"]),
                ("मेहताब", ["Mehtab"]), ("नौशाद", ["Naushad", "Noushad"]), ("राशिद", ["Rashid"]), ("शमशाद", ["Shamshad"])]
MUSLIM_FEMALE += [("आयशा", ["Ayesha", "Aisha"]), ("बुशरा", ["Bushra"]), ("फातिमा", ["Fatima", "Fatma"]), ("गुलनाज", ["Gulnaz"]),
                  ("हुमा", ["Huma"]), ("इशरत", ["Ishrat"]), ("जैनब", ["Zainab", "Jainab"]), ("खुशनुमा", ["Khushnuma"]),
                  ("मेहरुन", ["Mehrun", "Meharun"]), ("नूरजहाँ", ["Noorjahan", "Nurjahan"]), ("रजिया", ["Razia", "Rajiya"]),
                  ("सबीना", ["Sabina", "Sabeena"]), ("तबस्सुम", ["Tabassum"]), ("यास्मीन", ["Yasmeen", "Yasmin"]),
                  ("जुबैदा", ["Zubaida", "Jubaida"]), ("अकीला", ["Akila", "Aqeela"]), ("शहनाज", ["Shahnaz"]), ("मुन्नी", ["Munni"])]
BENGALI_MALE += [("असीम", ["Asim", "Ashim"]), ("बिप्लब", ["Biplab", "Viplav"]), ("चन्दन", ["Chandan"]), ("देबाशीष", ["Debashish", "Debasis"]),
                 ("गौतम", ["Gautam", "Goutam"]), ("जयन्त", ["Jayanta", "Jayant"]), ("कृष्णपद", ["Krishnapada"]), ("मनोरंजन", ["Manoranjan"]),
                 ("नारायण", ["Narayan"]), ("परिमल", ["Parimal"]), ("रतन", ["Ratan"]), ("सुशान्त", ["Sushanta", "Sushant"]),
                 ("उत्तम", ["Uttam"]), ("अनिमेष", ["Animesh"]), ("हरिदास", ["Haridas"])]
BENGALI_FEMALE += [("अपर्णा", ["Aparna"]), ("बीथिका", ["Bithika"]), ("दीपाली", ["Dipali", "Deepali"]), ("झरना", ["Jharna"]),
                   ("काकली", ["Kakali"]), ("मौसमी", ["Mousumi", "Mausami"]), ("नमिता", ["Namita"]), ("प्रतिमा", ["Pratima"]),
                   ("रीता", ["Rita", "Reeta"]), ("शम्पा", ["Shampa", "Sampa"]), ("तापसी", ["Tapasi"]), ("उषा", ["Usha"])]
