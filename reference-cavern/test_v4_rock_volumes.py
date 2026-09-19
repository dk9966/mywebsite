"""Check solid coverage and absence of overlapping BSP block interiors."""
import random, unittest
from v4_rock_volumes import volume, subtract, subdivide, partitions, surface_steps

def overlap(a,b):
    return all(min(a[2*i+1],b[2*i+1])-max(a[2*i],b[2*i])>1e-8 for i in range(3))

def contains(b,p):
    return all(b[2*i]-1e-8<=p[i]<=b[2*i+1]+1e-8 for i in range(3))

class SolidRockTests(unittest.TestCase):
    def test_recursive_partition_preserves_volume_without_overlaps(self):
        box=(-4,5,-3,4,-8,7)
        leaves=subdivide(box,random.Random(416))
        self.assertAlmostEqual(sum(map(volume,leaves)),volume(box),places=7)
        for i,a in enumerate(leaves):
            self.assertTrue(all(a[2*k]>=box[2*k] and a[2*k+1]<=box[2*k+1] for k in range(3)))
            for b in leaves[i+1:]:self.assertFalse(overlap(a,b))
    def test_exterior_carving_keeps_support_core_continuous(self):
        bounds=(-4,4,-4,4,-20,8)
        leaves,solids,cuts=partitions('Support test',bounds,'support')
        self.assertAlmostEqual(sum(map(volume,leaves)),sum(map(volume,solids)),places=7)
        for z in range(-20,9):
            for x in [-1.8,0,1.8]:
                for y in [-1.8,0,1.8]:
                    self.assertTrue(any(contains(b,(x,y,z)) for b in leaves))
    def test_surface_retreat_keeps_core_and_does_not_expand_blocks(self):
        bounds=(-4,4,-4,4,-20,8)
        leaves,_,_=partitions('Support test',bounds,'support')
        stepped=surface_steps(leaves,bounds,'support')
        for original,recessed in zip(leaves,stepped):
            for k in range(3):
                self.assertGreaterEqual(recessed[2*k],original[2*k])
                self.assertLessEqual(recessed[2*k+1],original[2*k+1])
        for z in range(-20,9):
            self.assertTrue(any(contains(b,(0,0,z)) for b in stepped))

    def test_cut_removes_exact_interior_volume(self):
        box=(0,10,0,10,0,10);cut=(2,7,1,8,3,9);parts=subtract(box,cut)
        self.assertAlmostEqual(sum(map(volume,parts)),volume(box)-volume(cut))
        for i,a in enumerate(parts):
            self.assertFalse(overlap(a,cut))
            for b in parts[i+1:]:self.assertFalse(overlap(a,b))

if __name__=='__main__':unittest.main()
