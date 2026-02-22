-- Update Zac's milestone achievement dates to match original PDF report
-- Generated from Development Report dated December 30, 2025

UPDATE milestones SET date_achieved = '2025-05-15 00:00:00'
WHERE child_id = 1 AND title IN (
  'Walks alone', 'Walks independently', 'Crawls up stairs',
  'Builds tower of 2-3 blocks', 'Drinks from a cup with some spilling',
  'Finger feeds efficiently', 'Gets into sitting position independently',
  'Pulls up to stand, walks holding onto furniture',
  'May take a few steps without holding on', 'May stand alone',
  'Sits without support', 'Crawls or creeps on hands and knees',
  'Pokes with index finger', 'Uses pincer grasp (thumb and forefinger)',
  'Feeds self finger foods', 'Tries to use spoon', 'Drinks from a cup',
  'Passes toys from one hand to another', 'Walks up and down stairs with support',
  'Babbles with increasing intonation', 'Responds to their name',
  'Understands many more words than they can say',
  'Communicates wants and needs with gestures', 'Responds to simple spoken requests',
  'Uses simple gestures like shaking head ''no'' or waving ''bye-bye''',
  'Makes sounds with changes in tone',
  'Says ''mama'' and ''dada'' and exclamations like ''uh-oh!''',
  'Tries to say words you say', 'Uses 1-3 words meaningfully',
  'Understands words like ''no'' and ''bye-bye''', 'Says ''mama'' and ''dada''',
  'Uses 6-20 single words', 'Begins combining two words',
  'Follows two-step instructions', 'Answers simple questions',
  'Uses 50+ single words', 'Points to pictures in books when named',
  'Responds to simple verbal requests', 'Finds hidden objects',
  'Shows interest in picture books', 'Imitates actions and simple tasks',
  'Remembers where objects belong', 'Explores objects in different ways',
  'Finds hidden objects easily',
  'Looks at the right picture or thing when it''s named',
  'Imitates gestures', 'Explores objects by banging, shaking, throwing',
  'Puts things in a container, takes things out', 'Bangs two things together',
  'Starts to use things correctly', 'Lets things go without help',
  'Points to get others'' attention', 'Follows one-step verbal instructions',
  'Shows separation anxiety', 'Enjoys interactive games like peek-a-boo',
  'Shows affection to familiar people', 'Is shy or nervous with strangers',
  'Imitates household activities', 'Has favorite people and things',
  'Cries when parent leaves', 'Tests parental responses to behavior',
  'Shows fear in some situations',
  'Hands you a book when wanting to hear a story',
  'Repeats sounds or actions to get attention',
  'Plays games such as peek-a-boo and pat-a-cake',
  'Hands toy to adult for help', 'Puts out arm or leg to help with dressing'
) AND is_achieved = true;

UPDATE milestones SET date_achieved = '2025-05-16 00:00:00'
WHERE child_id = 1 AND title IN (
  'Kicks a ball', 'Scribbles with crayon or pencil',
  'Begins using spoon and fork', 'Runs with increasing coordination',
  'Throws ball overhand', 'Follows 2-3 step instructions',
  'Uses pronouns (I, me, you)', 'Asks simple questions',
  'Speaks in 2-3 word sentences', 'Uses 200+ words',
  'Matches similar objects', 'Follows picture book stories',
  'Recognizes self in mirror', 'Sorts objects by category',
  'Names familiar objects and pictures', 'Follows story sequence in books',
  'Shows increasing independence', 'Engages in pretend play',
  'Begins to express emotions with words',
  'Shows interest in helping with simple tasks', 'Refers to self by name',
  'Engages in parallel play',
  'Copies others, especially adults and older children',
  'Takes turns with assistance', 'Plays alongside other children'
) AND is_achieved = true;

UPDATE milestones SET date_achieved = '2025-05-31 00:00:00'
WHERE child_id = 1 AND title IN (
  'Builds tower of 4-6 blocks'
) AND is_achieved = true;

UPDATE milestones SET date_achieved = '2025-06-08 00:00:00'
WHERE child_id = 1 AND title IN (
  'Walks up and down stairs alone',
  'Knows names of familiar people and body parts',
  'Says sentences with 2 to 4 words', 'Follows simple instructions',
  'Repeats words overheard in conversation', 'Points to things in a book',
  'Names items in a picture book (e.g., cat, bird, dog)',
  'Points to things or pictures when they are named',
  'Uses at least 50 words'
) AND is_achieved = true;

UPDATE milestones SET date_achieved = '2025-06-18 00:00:00'
WHERE child_id = 1 AND title IN (
  'Stands on tiptoe', 'Climbs onto and down from furniture without help',
  'Begins to run', 'Scribbles spontaneously',
  'Helps with dressing (puts arm in sleeve)',
  'Might use one hand more than the other',
  'Uses spoon and cup independently',
  'Plays simple make-believe games',
  'Names items in a picture book',
  'Completes sentences and rhymes in familiar books',
  'Shows defiant behavior'
) AND is_achieved = true;

UPDATE milestones SET date_achieved = '2025-12-30 00:00:00'
WHERE child_id = 1 AND title IN (
  'Walks up and down stairs holding on', 'Builds towers of 4 or more blocks',
  'Turns pages in a book, one at a time', 'Jumps with both feet',
  'Uses scissors to snip paper', 'Draws simple shapes',
  'Speaks clearly enough for familiar listeners', 'Begins using plural words',
  'Engages in short conversations', 'Sorts objects by shape or color',
  'Finds things even when hidden under two or three covers',
  'Begins to sort shapes and colors', 'Completes simple puzzles',
  'Understands concept of ''one'' and ''two''',
  'Remembers and recites parts of stories', 'Engages in complex pretend play',
  'Understands concept of ''big'' and ''little''',
  'Shows first friendships', 'Shows more complex emotions',
  'Plays mainly beside other children', 'Separates more easily from parents',
  'Engages in more complex pretend play'
) AND is_achieved = true;
