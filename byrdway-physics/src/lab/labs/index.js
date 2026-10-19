// Registry of the 20 signature laboratories (numbered as in the owner's Video Link Library).
import lab05 from './lab05.js';

export const LABS = [lab05].sort((a, b) => a.num - b.num);
export const findLab = n => LABS.find(l => l.num === Number(n));
