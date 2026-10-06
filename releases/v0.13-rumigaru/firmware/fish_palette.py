"""Three restrained fish colourways; stable semantic roles for imported parts."""
def colors(index):
    primary=(
        ((24,43,49),(43,85,88),(77,134,135)),
        ((26,33,71),(48,65,132),(78,112,194)),
        ((49,29,61),(95,56,104),(145,95,151)),
    )[index%3]
    return ((0,0,0),(9,14,35),primary[0],primary[1],primary[2],
            (190,166,127),(249,235,195),(64,222,221),(247,178,37),
            (134,186,211),(133,117,101),(255,251,220))
