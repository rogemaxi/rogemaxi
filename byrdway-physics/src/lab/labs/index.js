// Registry of the 20 signature laboratories (numbered as in the owner's Video Link Library).
import lab01 from './lab01.js'; import lab02 from './lab02.js'; import lab03 from './lab03.js'; import lab04 from './lab04.js';
import lab05 from './lab05.js'; import lab06 from './lab06.js'; import lab07 from './lab07.js'; import lab08 from './lab08.js';
import lab09 from './lab09.js'; import lab10 from './lab10.js'; import lab11 from './lab11.js';

export const LABS = [lab01, lab02, lab03, lab04, lab05, lab06, lab07, lab08, lab09, lab10, lab11].sort((a, b) => a.num - b.num);
export const findLab = n => LABS.find(l => l.num === Number(n));
