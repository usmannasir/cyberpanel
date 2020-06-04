Branches

    1.Stable-> Stable branch
    2.vX.X.X-> vX.X.X Stable branch
    3.vX.X.X-dev-> v.X.X.X Dev branch

Development Lifecycle

    vX.X.X-dev will be default(master) branch. All contributors must push to latest vX.X.X-dev branch. Once development
    is complete(believed to be stable) new vX.X.X Stable branch will be created from Dev branch. Then vX.X.X Stable will
    be merged into Stable branch. After that a new vX.X.X-dev branch will be created and it will be default(master) 
    branch. Old dev branch will be deleted at this stage(to save space) and no development will happen on old stable or 
    dev(if not deleted) branch. All development will only take place in latest dev branch. You must not create pull 
    request for any other branches other than latest dev branch.
