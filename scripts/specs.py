# Per-typeface layout on the scanned sheet: block region, threshold, and for each
# text line its rough y-range (component centres) and the glyph names it shows.
D = lambda s: s.split()
SPECS = {
 'kilfane': dict(box=(40,118,405,382), T=160, lines=[
   ((118,160), D('A B C D E F G H I J K L M')),
   ((160,205), D('N O P Q R S T U V W X Y')),
   ((205,255), D('Z a b c d e f g h i j k l m n o')),
   ((255,294), D('p q r s t u v w x y z ornament')),
   ((294,332), D('one two three four five six seven eight nine zero ampersand question exclam sterling dollar parenleft semicolon parenright')),
   ((332,380), D('A.alt1 A.alt2 D.alt1 S.alt1 T.alt1 Y.alt1 d.alt1 f.alt1 g.alt1 l.alt1 t.alt1 y.alt1')),
 ], force={'ornament': (314, 376)},
   split=[(1,145,2),(1,247,2,[249.5]),(1,310,2),(2,221,2),(2,300,2),(3,128,2),(3,171,2),(3,219,2,[213.5])]),
 'tuam': dict(box=(420,118,790,312), T=160, lines=[
   ((118,162), D('a b c d e f g h i j k l')),
   ((162,200), D('m n o p q r s t u v')),
   ((200,237), D('w x y z one two three four five six seven')),
   ((237,276), D('eight nine zero sterling dollar ampersand question exclam aacute eacute iacute')),
   ((276,312), D('oacute uacute')),
 ], force={'m': (436,480), 'n': (480,510), 'y': (509,537)}),
 'carrick': dict(box=(40,530,405,702), T=160, lines=[
   ((530,580), D('a b c d e f g h i j k l m')),
   ((580,620), D('n o p q r s t u v w x')),
   ((620,660), D('y z one two three four five six seven eight nine zero')),
   ((660,702), D('ampersand question exclam sterling dollar parenleft semicolon parenright ornament')),
 ], force={'ornament': (204, 272), 'k': (306, 338)},
   split=[(0,117,2)]),
 'ceili': dict(box=(420,528,790,706), T=160, lines=[
   ((528,576), D('a a.alt1 a.alt2 b c d d.alt1 e e.alt1 f g h i')),
   ((576,619), D('j j.alt1 k l l.alt1 m n n.alt1 o p q r r.alt1 s')),
   ((619,664), D('s.alt1 t u v v.alt1 w x y ampersand z parenleft DOTS parenright')),
   ((664,706), D('zero one two three four five six seven eight nine sterling dollar question exclam hyphen')),
 ], force={'DOTS': (734, 757)}),
}
