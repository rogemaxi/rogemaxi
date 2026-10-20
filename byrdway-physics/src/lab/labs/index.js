// Registry of the 20 signature laboratories (numbered as in the owner's Video Link Library).
import lab01 from './lab01.js'; import lab02 from './lab02.js'; import lab03 from './lab03.js'; import lab04 from './lab04.js';
import lab05 from './lab05.js'; import lab06 from './lab06.js'; import lab07 from './lab07.js'; import lab08 from './lab08.js';
import lab09 from './lab09.js'; import lab10 from './lab10.js'; import lab11 from './lab11.js'; import lab12 from './lab12.js';
import lab13 from './lab13.js'; import lab14 from './lab14.js'; import lab15 from './lab15.js'; import lab16 from './lab16.js';
import lab17 from './lab17.js'; import lab18 from './lab18.js'; import lab19 from './lab19.js'; import lab20 from './lab20.js';

export const LABS = [lab01, lab02, lab03, lab04, lab05, lab06, lab07, lab08, lab09, lab10, lab11, lab12, lab13, lab14, lab15, lab16, lab17, lab18, lab19, lab20];
export const findLab = n => LABS.find(l => l.num === Number(n));
